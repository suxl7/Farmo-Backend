from collections import defaultdict
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from backend.permissions import HasValidTokenForUser, IsFarmer, IsAdmin
from rest_framework import status
from backend.models import Users, Product, FarmProducts, Connections, ProductRating, OrderRequest, ProductScore, Rating
from backend.serializers import ProductSerializer
from backend.utils.media_handler import FileManager
from django.utils.dateparse import parse_date
import json
import secrets


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

PAGE_SIZE             = 10
EXPIRY_NEAR_DAYS      = 7    # ≤  7 days  → exclude if non-local; boost if municipal
EXPIRY_MUNICIPAL_DAYS = 15   # ≤ 15 days  → recommend from same municipal
EXPIRY_DISTRICT_DAYS  = 20   # ≤ 20 days  → recommend from same district
EXPIRY_PROVINCE_DAYS  = 30   # > 20 days  → recommend from same province
EXPIRY_RADIUS_DAYS    = 30   # legacy alias
EXPIRY_WIDE_DAYS      = 90   # ≤ 90 days  → district radius (legacy)

VALID_FILTERS = {"all", "connectiononly", "nearme"}

# Composite score weights
W_LOCATION_TIER    = 100   # per tier level (×0–4)
W_CONNECTION_BONUS = 200   # bonus for connected farmers
W_RATING           = 20    # per rating point (0–5 scale → 0–100)
W_SOLD             = 3     # per delivered order (capped at 100 orders)
W_CATEGORY_SCORE   = 1     # multiplier for user's ProductScore category score
W_KEYWORD_SCORE    = 2     # multiplier for user's ProductScore farm-product score


# ─────────────────────────────────────────────
# BASE QUERYSET  (exclude own + inactive)
# ─────────────────────────────────────────────

def _active_products_qs(exclude_user_id: str | None = None):
    """
    Active, in-stock, non-expired products.
    Excludes the requesting user's own listings.
    """
    today = timezone.now().date()
    qs = (
        Product.objects
        .filter(
            product_status="Available",
            quantity_available__gt=0,
        )
        .filter(Q(expiry_Date__isnull=True) | Q(expiry_Date__gt=today))
        .select_related("user_id__profile_id")
    )
    if exclude_user_id:
        qs = qs.exclude(user_id__user_id=exclude_user_id)
    return qs


# ─────────────────────────────────────────────
# BATCH STAT HELPERS
# ─────────────────────────────────────────────

def _batch_fetch_stats(product_ids: list) -> tuple[dict, dict]:
    """
    Single-pass batch fetch of average ratings and DELIVERED order counts.
    Returns (ratings_map, sold_map) keyed by p_id.
    """
    ratings = (
        ProductRating.objects
        .filter(p_id__in=product_ids)
        .values("p_id")
        .annotate(avg_rating=Avg("score"))
    )
    ratings_map = {r["p_id"]: float(r["avg_rating"] or 0) for r in ratings}

    sold = (
        OrderRequest.objects
        .filter(product__in=product_ids, order_status="DELIVERED")
        .values("product")
        .annotate(count=Count("order_id"))
    )
    sold_map = {s["product"]: s["count"] for s in sold}

    return ratings_map, sold_map


def _get_track_stats(user: Users) -> tuple[dict, dict]:
    """
    Returns:
        category_scores  – {category_slug: total_score}
        product_scores   – {farm_product_id: total_score}
    """
    tracks = ProductScore.objects.filter(user_id=user).select_related("farmProduct")
    category_scores: dict = defaultdict(int)
    product_scores: dict  = defaultdict(int)

    for t in tracks:
        score = t.score or 0
        if t.product_catagory:
            category_scores[t.product_catagory] += score
        if t.farmProduct_id:
            product_scores[t.farmProduct_id] += score

    return dict(category_scores), dict(product_scores)


def _get_connection_farmer_ids(user: Users) -> list:
    """Return user_ids of ACCEPTED connections where target is Farmer/VerifiedFarmer."""
    accepted = Connections.objects.filter(
        user=user, status="ACCEPTED"
    ).select_related("target_user__profile_id")

    return [
        conn.target_user.user_id
        for conn in accepted
        if conn.target_user.profile_id.user_type in ("Farmer", "VerifiedFarmer")
    ]


# ─────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────

def _location_tier(farmer_profile, user_profile) -> int:
    """
    Returns 0–4:
        4 = same ward + municipal
        3 = same municipal
        2 = same district
        1 = same province
        0 = nationwide
    """
    if (
        farmer_profile.ward
        and farmer_profile.ward == user_profile.ward
        and farmer_profile.municipal == user_profile.municipal
    ):
        return 4
    if farmer_profile.municipal == user_profile.municipal:
        return 3
    if farmer_profile.district == user_profile.district:
        return 2
    if farmer_profile.province == user_profile.province:
        return 1
    return 0


def _compute_score(
    product, user_profile,
    category_scores: dict, product_scores: dict,
    ratings_map: dict, sold_map: dict,
    connection_bonus: bool = False,
) -> float:
    """
    Composite ranking score (higher = shown earlier).

    Components:
        1. Location tier        (0–400 pts)
        2. User interest        (category + keyword match from ProductScore)
        3. Average rating       (0–100 pts)
        4. Sold/delivered count (capped, 0–300 pts)
        5. Connection bonus     (+200 pts if farmer is connected)
    """
    farmer_profile = product.user_id.profile_id
    s = 0.0

    # 1. Location
    tier = _location_tier(farmer_profile, user_profile)
    s += tier * W_LOCATION_TIER

    # 2. User interest: keyword-level score
    keywords = product.keywords or []
    if isinstance(keywords, list):
        for kw in keywords:
            s += product_scores.get(kw, 0) * W_KEYWORD_SCORE

    # 2b. Category-level score
    if product.product_type:
        s += category_scores.get(product.product_type, 0) * W_CATEGORY_SCORE

    # 3. Rating  (0–5 → 0–100)
    avg_rating = ratings_map.get(product.p_id, 0.0)
    s += avg_rating * W_RATING

    # 4. Sold count (capped at 100 to avoid outlier dominance)
    sold = sold_map.get(product.p_id, 0)
    s += min(sold, 100) * W_SOLD

    # 5. Connection bonus
    if connection_bonus:
        s += W_CONNECTION_BONUS

    return s


# ─────────────────────────────────────────────
# FILTER / RANK  (shared pipeline)
# ─────────────────────────────────────────────

def _filter_and_rank(
    products: list,
    user_profile,
    category_scores: dict,
    product_scores: dict,
    connection_farmer_ids: set | None = None,
) -> tuple[list, dict, dict]:
    """
    Shared ranking pipeline used by all three feed filters.
    NOT used by search — search has its own expiry gate that
    preserves match_count order.

    Steps
    -----
    1. Hard-exclude products expiring within EXPIRY_NEAR_DAYS (7d) from
       non-local (outside district) farmers.
    2. Score every surviving product with _compute_score.
    3. Collect local near-expiry products (≤7d, district-or-closer) —
       they jump to slot [1] after the top-scored item.
    4. Final order:
           [highest_score] + [near_expiry_local…] + [rest by score…]

    Returns (ranked_products, ratings_map, sold_map).
    """
    today        = timezone.now().date()
    product_ids  = [p.p_id for p in products]
    ratings_map, sold_map = _batch_fetch_stats(product_ids)

    if connection_farmer_ids is None:
        connection_farmer_ids = set()

    regular: list[tuple]  = []
    near_expiry_local: list = []

    for product in products:
        farmer_profile = product.user_id.profile_id
        tier      = _location_tier(farmer_profile, user_profile)
        is_local  = tier >= 2  # district or closer

        # ── Hard expiry gate ─────────────────────
        if product.expiry_Date:
            days_left = (product.expiry_Date - today).days
            if days_left <= EXPIRY_NEAR_DAYS:
                if not is_local:
                    continue                          # far + near-expiry → drop
                near_expiry_local.append(product)    # local near-expiry → top slot
                continue

        # ── Composite score ──────────────────────
        in_connection = product.user_id.user_id in connection_farmer_ids
        s = _compute_score(
            product, user_profile,
            category_scores, product_scores,
            ratings_map, sold_map,
            connection_bonus=in_connection,
        )
        regular.append((product, s))

    # Primary sort: score descending
    regular.sort(key=lambda x: x[1], reverse=True)
    ranked = [p for p, _ in regular]

    # Urgent local near-expiry products → slot [1]
    if near_expiry_local and ranked:
        ranked = ranked[:1] + near_expiry_local + ranked[1:]
    elif near_expiry_local:
        ranked = near_expiry_local

    return ranked, ratings_map, sold_map


# ─────────────────────────────────────────────
# SEARCH
# ─────────────────────────────────────────────

def _rank_search_results(
    products: list,
    user_profile,
    category_scores: dict,
    product_scores: dict,
    connection_farmer_ids: set,
    ratings_map: dict,
    sold_map: dict,
) -> list:
    """
    Rank a list of products by composite score (used inside each search tier).
    """
    scored = []
    for p in products:
        s = _compute_score(
            p, user_profile,
            category_scores, product_scores,
            ratings_map, sold_map,
            connection_bonus=(p.user_id.user_id in connection_farmer_ids),
        )
        scored.append((p, s))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in scored]


def _resolve_farmproduct_categories(search_term: str) -> tuple[list, list, list]:
    """
    Given a search term, return:
        matched_fp_ids      – IDs of FarmProducts whose name matches
        related_categories  – category slugs of those FarmProducts
        all_fp_ids          – all FarmProduct IDs in those categories
    """
    matching_fps = FarmProducts.objects.filter(
        Q(primary_name__icontains=search_term)   |
        Q(secondary_name__icontains=search_term) |
        Q(category__icontains=search_term)
    )
    matched_fp_ids     = list(matching_fps.values_list("id", flat=True))
    related_categories = list(matching_fps.values_list("category", flat=True).distinct())

    all_fp_ids = list(
        FarmProducts.objects
        .filter(
            Q(id__in=matched_fp_ids) |
            Q(category__in=related_categories)
        )
        .values_list("id", flat=True)
    )
    return matched_fp_ids, related_categories, all_fp_ids


def _search_single_term(
    search_term: str,
    user_profile,
    base_qs,
    user,
    category_scores: dict,
    product_scores: dict,
    connection_farmer_ids: set,
) -> list:
    """
    Single-term tiered search.

    ═══ PHASE 1 — Direct match (tiers 0–3) ════════════════════════════════════
        Tier 0  exact p_id              e.g. "farmer-P-R2fPk9eu6FW45Q"
        Tier 1  product.name            icontains
        Tier 2  product.product_type    resolved via FarmProduct category slug
        Tier 3  product.keywords        FarmProduct ID in keywords JSON list
                                        AND product_type in resolved categories

        Each tier is ranked by composite score independently.
        A product only appears in its highest matching tier (no duplicates).

    ═══ PHASE 2 — Category expansion fallback ══════════════════════════════════
        If Tiers 1–3 return nothing:
            • Look up the searched term in FarmProducts (name + category slug)
            • Find the parent category  (e.g. "rice" → "grain")
            • Fetch ALL products in that category from the DB
            • sibling keyword branch also filtered by product_type  ← bug fix
              (old code didn't do this → oil/unrelated products appeared)
    """
    seen: set = set()

    # ── Resolve FarmProduct metadata once ────────────────────────────────────
    matched_fp_ids, related_categories, all_fp_ids = _resolve_farmproduct_categories(search_term)

    # ── Tier 0: p_id match ──────────────────────────────────────────────────
    tier0: list = []
    pid_matches = list(base_qs.filter(p_id__icontains=search_term).exclude(p_id__in=seen))
    if pid_matches:
        exact  = [p for p in pid_matches if p.p_id.lower() == search_term.lower()]
        others = [p for p in pid_matches if p.p_id.lower() != search_term.lower()]
        tier0  = exact + others
        seen.update(p.p_id for p in tier0)

    # ── Tier 1: product name ─────────────────────────────────────────────────
    tier1_raw = list(
        base_qs
        .filter(name__icontains=search_term)
        .exclude(p_id__in=seen)
    )
    seen.update(p.p_id for p in tier1_raw)

    # ── Tier 2: product_type via FarmProduct category resolution ─────────────
    tier2_raw: list = []
    if related_categories:
        tier2_raw = list(
            base_qs
            .filter(product_type__in=related_categories)
            .exclude(p_id__in=seen)
            .distinct()
        )
        seen.update(p.p_id for p in tier2_raw)

    # ── Tier 3: keywords (FarmProduct ID in JSON list) ───────────────────────
    tier3_raw: list = []
    if all_fp_ids:
        kw_q = Q()
        for fp_id in all_fp_ids:
            kw_q |= Q(keywords__contains=[fp_id])

        tier3_qs = base_qs.filter(kw_q).exclude(p_id__in=seen)

        if related_categories:
            tier3_qs = tier3_qs.filter(product_type__in=related_categories)

        tier3_raw = list(tier3_qs.distinct())
        seen.update(p.p_id for p in tier3_raw)

    # ── Batch stats for ranking (one pass for all tiers) ─────────────────────
    direct_products = tier0 + tier1_raw + tier2_raw + tier3_raw
    if direct_products:
        ratings_map, sold_map = _batch_fetch_stats([p.p_id for p in direct_products])
    else:
        ratings_map, sold_map = {}, {}

    def _rank(lst):
        return _rank_search_results(
            lst, user_profile,
            category_scores, product_scores,
            connection_farmer_ids,
            ratings_map, sold_map,
        )

    tier1_ranked = _rank(tier1_raw)
    tier2_ranked = _rank(tier2_raw)
    tier3_ranked = _rank(tier3_raw)

    direct_results = tier0 + tier1_ranked + tier2_ranked + tier3_ranked

    # ── Phase 2: category-expansion fallback ─────────────────────────────────
    # Triggered when tiers 1–3 all returned nothing (tier 0 stands alone).
    category_results: list = []
    if not (tier1_raw or tier2_raw or tier3_raw) and related_categories:
        fallback_qs = (
            base_qs
            .filter(product_type__in=related_categories)
            .exclude(p_id__in=seen)
        )

        if all_fp_ids:
            sib_q = Q()
            for fp_id in all_fp_ids:
                sib_q |= Q(keywords__contains=[fp_id])

            # FIX: enforce product_type so off-category products never appear
            sibling_qs = (
                base_qs
                .filter(sib_q)
                .filter(product_type__in=related_categories)
                .exclude(p_id__in=seen)
            )
            fallback_qs = (fallback_qs | sibling_qs).distinct()

        fallback_products = list(fallback_qs.distinct())
        seen.update(p.p_id for p in fallback_products)

        if fallback_products:
            fb_ratings, fb_sold = _batch_fetch_stats(
                [p.p_id for p in fallback_products]
            )
            category_results = _rank_search_results(
                fallback_products, user_profile,
                category_scores, product_scores,
                connection_farmer_ids,
                fb_ratings, fb_sold,
            )

    return direct_results + category_results


def _search_products(
    search_term: str,
    user_profile,
    base_qs,
    user,
    category_scores: dict,
    product_scores: dict,
    connection_farmer_ids: set,
) -> list:
    """
    Multi-word aware search entry point.

    Algorithm
    ─────────
    1. Split query by whitespace → individual words.
       "basmati rice" → ["basmati", "rice"]

    2. Run _search_single_term for EACH word independently.
       "rice" alone resolves FarmProducts → category "grain" → all grain products.
       "basmati" alone resolves name match or its own category.

    3. Run _search_single_term for the FULL PHRASE (bonus pass).
       Products that match the full phrase get +len(words) extra match points,
       floating them above partial matches.

    4. Deduplicate across all results.
       match_count tracks how many individual words each product matched.
       Products matching MORE words rank first.

    5. Within same match_count, insertion order (= tier order) is preserved.

    Single-word queries bypass splitting (no overhead).

    Example
    ───────
    Query: "basmati rice"

    Word "basmati" → Tier 1: product named "Basmati"           → match_count +1
    Word "rice"    → Tier 2: category "grain" → grain products → match_count +1
    Phrase         → Tier 1: product "Basmati Rice"            → match_count +2 (bonus)

    "Basmati Rice" product → 4 pts  ← floats to top
    "Brown Rice"   product → 1 pt
    "Wheat Grain"  product → 1 pt   ← also from grain category
    """
    words = [w.strip() for w in search_term.split() if w.strip()]
    if not words:
        return []

    # Single-word fast path
    if len(words) == 1:
        return _search_single_term(
            words[0], user_profile, base_qs, user,
            category_scores, product_scores, connection_farmer_ids,
        )

    # ── Multi-word path ───────────────────────────────────────────────────────
    match_count: dict[str, int]    = defaultdict(int)
    product_map: dict[str, object] = {}   # p_id → Product (first/highest-tier encounter)

    # Pass 1: search each word independently
    for word in words:
        word_results = _search_single_term(
            word, user_profile, base_qs, user,
            category_scores, product_scores, connection_farmer_ids,
        )
        for p in word_results:
            if p.p_id not in product_map:
                product_map[p.p_id] = p    # first encounter = highest tier position
            match_count[p.p_id] += 1

    # Pass 2: full-phrase bonus
    phrase_results = _search_single_term(
        search_term, user_profile, base_qs, user,
        category_scores, product_scores, connection_farmer_ids,
    )
    for p in phrase_results:
        if p.p_id not in product_map:
            product_map[p.p_id] = p
        match_count[p.p_id] += len(words)   # phrase match = as if all words matched again

    # Sort by match_count descending; ties preserve insertion order (tier order)
    sorted_pids = sorted(
        product_map.keys(),
        key=lambda pid: match_count[pid],
        reverse=True,
    )
    return [product_map[pid] for pid in sorted_pids]


def _apply_search_expiry_gate(
    search_results: list,
    user_profile,
    connection_farmer_ids: set,
) -> tuple[list, dict, dict]:
    """
    Applies only the expiry gate on search results WITHOUT re-ranking by score.
    This preserves the match_count order from _search_products.

    Rules (same as _filter_and_rank):
        - Product expiring in ≤ 7 days AND farmer is non-local  → dropped
        - Product expiring in ≤ 7 days AND farmer is local      → slot [1]
        - All other products                                     → kept in order

    Returns (ranked, ratings_map, sold_map).
    """
    today = timezone.now().date()

    product_ids = [p.p_id for p in search_results]
    ratings_map, sold_map = _batch_fetch_stats(product_ids) if product_ids else ({}, {})

    ranked: list           = []
    near_expiry_local: list = []

    for product in search_results:   # order is match_count order — preserve it
        farmer_profile = product.user_id.profile_id
        tier     = _location_tier(farmer_profile, user_profile)
        is_local = tier >= 2

        if product.expiry_Date:
            days_left = (product.expiry_Date - today).days
            if days_left <= EXPIRY_NEAR_DAYS:
                if not is_local:
                    continue                           # far + near-expiry → drop
                near_expiry_local.append(product)     # local urgent → slot [1]
                continue

        ranked.append(product)   # preserved match_count order

    # Inject urgent local products at slot [1]
    if near_expiry_local and ranked:
        ranked = ranked[:1] + near_expiry_local + ranked[1:]
    elif near_expiry_local:
        ranked = near_expiry_local

    return ranked, ratings_map, sold_map


# ─────────────────────────────────────────────
# FEED STRATEGIES
# ─────────────────────────────────────────────

def _get_top_rated_farmer_products(base_qs, user_profile, exclude_ids: set, limit: int = 5) -> list:
    """
    Returns up to `limit` products from the highest-rated farmers.
    Used to inject quality signals at the top of the feed.
    """
    top_farmer_ids = (
        Rating.objects
        .filter(rated_for="Farmer")
        .values("rated_to")
        .annotate(avg=Avg("score"))
        .order_by("-avg")
        .values_list("rated_to", flat=True)[:20]
    )

    if not top_farmer_ids:
        return []

    products = list(
        base_qs
        .filter(user_id__in=top_farmer_ids)
        .exclude(p_id__in=exclude_ids)
        .order_by("-registered_at")[:limit]
    )
    return products


def _get_expiry_recommendations(base_qs, user_profile, exclude_ids: set) -> list:
    """
    Expiry-aware local recommendations injected at the end of the feed.

    Rules
    ─────
    ≤ 15 days left  →  same municipal
    ≤ 20 days left  →  same district
    > 20 days left  →  same province
    """
    today = timezone.now().date()

    d15 = today + timedelta(days=EXPIRY_MUNICIPAL_DAYS)
    d20 = today + timedelta(days=EXPIRY_DISTRICT_DAYS)

    # Bucket 1 — municipal, expiring within 15 days
    municipal = list(
        base_qs
        .filter(
            user_id__profile_id__municipal=user_profile.municipal,
            expiry_Date__gt=today,
            expiry_Date__lte=d15,
        )
        .exclude(p_id__in=exclude_ids)
        .order_by("expiry_Date")
    )

    seen = exclude_ids | {p.p_id for p in municipal}

    # Bucket 2 — district, expiring 15–20 days
    district = list(
        base_qs
        .filter(
            user_id__profile_id__district=user_profile.district,
            expiry_Date__gt=d15,
            expiry_Date__lte=d20,
        )
        .exclude(p_id__in=seen)
        .order_by("expiry_Date")
    )

    seen |= {p.p_id for p in district}

    # Bucket 3 — province, expiring > 20 days
    province = list(
        base_qs
        .filter(
            user_id__profile_id__province=user_profile.province,
            expiry_Date__gt=d20,
        )
        .exclude(p_id__in=seen)
        .order_by("expiry_Date")
    )

    return municipal + district + province


def _feed_all(
    user: Users, user_profile, base_qs,
    category_scores: dict, product_scores: dict,
    connection_farmer_ids: set | None = None,
) -> tuple[list, dict, dict]:
    """
    Full personalised feed for the "all" filter.

    Build order
    ───────────
    1. Score-filtered main feed (all active products scored + expiry gate)
    2. Top-rated farmer spotlight (up to 5, injected after slot [0])
    3. Expiry-aware location recommendations (appended at end)
    """
    if connection_farmer_ids is None:
        connection_farmer_ids = set(_get_connection_farmer_ids(user))

    all_products = list(base_qs.all())

    # Step 1: main ranked feed
    ranked, ratings_map, sold_map = _filter_and_rank(
        all_products, user_profile,
        category_scores, product_scores,
        connection_farmer_ids=connection_farmer_ids,
    )

    main_ids = {p.p_id for p in ranked}

    # Step 2: top-rated farmer spotlight
    top_rated = _get_top_rated_farmer_products(base_qs, user_profile, main_ids)
    top_rated_ids = {p.p_id for p in top_rated}

    if top_rated and ranked:
        ranked = ranked[:1] + top_rated + ranked[1:]
    elif top_rated:
        ranked = top_rated

    # Step 3: expiry-aware local recommendations
    exclude_so_far = main_ids | top_rated_ids
    expiry_recs = _get_expiry_recommendations(base_qs, user_profile, exclude_so_far)

    if expiry_recs:
        rec_ids = [p.p_id for p in expiry_recs]
        rec_ratings, rec_sold = _batch_fetch_stats(rec_ids)
        scored_recs = []
        for p in expiry_recs:
            s = _compute_score(
                p, user_profile, category_scores, product_scores,
                rec_ratings, rec_sold,
                connection_bonus=(p.user_id.user_id in connection_farmer_ids),
            )
            scored_recs.append((p, s))
        scored_recs.sort(key=lambda x: x[1], reverse=True)
        expiry_recs = [p for p, _ in scored_recs]

        ratings_map.update(rec_ratings)
        sold_map.update(rec_sold)

    ranked = ranked + expiry_recs

    return ranked, ratings_map, sold_map


def _feed_connection_only(
    user: Users, user_profile, base_qs,
    category_scores: dict, product_scores: dict,
) -> tuple[list, dict, dict]:
    """
    Products from ACCEPTED farmer connections only.
    """
    farmer_ids = _get_connection_farmer_ids(user)
    if not farmer_ids:
        return [], {}, {}

    products = list(base_qs.filter(user_id__in=farmer_ids))
    return _filter_and_rank(products, user_profile, category_scores, product_scores)


def _feed_near_me(
    user_profile, base_qs,
    category_scores: dict, product_scores: dict,
) -> tuple[list, dict, dict]:
    """
    Province/district/municipal products ranked by composite score.
    """
    qs = base_qs.filter(
        Q(user_id__profile_id__municipal=user_profile.municipal)
        | Q(user_id__profile_id__district=user_profile.district)
        | Q(user_id__profile_id__province=user_profile.province)
    )
    products = list(qs)
    return _filter_and_rank(products, user_profile, category_scores, product_scores)


# ─────────────────────────────────────────────
# SERIALISER
# ─────────────────────────────────────────────

def _serialize_product(
    product: Product,
    ratings_map: dict | None = None,
    sold_map: dict | None = None,
) -> dict:
    """
    Convert a Product ORM object to the API response dict.
    Pure serialiser — NO DB hits when ratings_map and sold_map are supplied.
    """
    today = timezone.now().date()

    if product.product_status == "Sold":
        display_status = "out_of_stock"
    elif product.expiry_Date and product.expiry_Date <= today:
        display_status = "inactive"
    elif product.quantity_available <= 0:
        display_status = "out_of_stock"
    else:
        display_status = "active"

    media = product.media_url or []
    if isinstance(media, dict):
        media = list(media.values())
    image = media[0] if media else ""

    if ratings_map is not None:
        avg_rating = ratings_map.get(product.p_id, 0.0)
    else:
        avg_rating = (
            ProductRating.objects.filter(p_id=product)
            .aggregate(avg_rating=Avg("score"))["avg_rating"]
        ) or 0.0

    if sold_map is not None:
        sold_count = sold_map.get(product.p_id, 0)
    else:
        sold_count = OrderRequest.objects.filter(
            product=product, order_status="DELIVERED"
        ).count()

    return {
        "id":            product.p_id,
        "name":          product.name,
        "product_type":  product.product_type,
        "status":        display_status,
        "discount_type": product.discount_type,
        "discount":      str(product.discount),
        "is_organic":    product.is_organic,
        "price":         str(product.cost_per_unit),
        "priceUnit":     "Rs.",
        "stock":         str(product.quantity_available),
        "stockUnit":     product.product_unit.lower(),
        "image":         image,
        "rating":        str(round(avg_rating, 1)),
        "sold_count":    sold_count,
    }


# ─────────────────────────────────────────────
# MAIN VIEW
# ─────────────────────────────────────────────
from backend.permissions import *

@api_view(["POST"])
@permission_classes([AllowAny, IsFarmerOrConsumer])
def get_product_feed(request):
    """
    POST /api/product/feed/

    Headers:
        user-id   (required)

    Body (JSON):
        page        : int  – default 1
        serial_no   : int  – default 1  (1-10 per page)
        filter      : str  – "all" | "connectiononly" | "nearme"  default "all"
        search_term : str  – optional; multi-word aware search

    Search behaviour:
        - Splits multi-word queries ("basmati rice" → ["basmati", "rice"])
        - Searches each word independently via 4-tier system
        - Products matching MORE words rank higher (match_count sorting)
        - Full-phrase match gets +len(words) bonus points
        - Expiry gate applied WITHOUT re-scoring (preserves match_count order)
        - Off-category products (oil when searching rice) are blocked by
          product_type guard in Phase 2 fallback

    Ranking logic (feed filters):
        1. Location tier     same ward > municipal > district > province > nationwide
        2. User interest     ProductScore (category & keyword scores)
        3. Average rating    higher = earlier
        4. Sold/delivered    higher = earlier (capped at 100)
        5. Connection bonus  +200 pts for accepted farmer connections
        6. Near-expiry gate  ≤7d non-local → excluded; local → slot [1]

    Response:
    {
        "page":        1,
        "serial_no":   1,
        "total_pages": 4,
        "has_more":    true,
        "filter":      "all",
        "product":     { ...product fields... }
    }
    """
    # ── Auth / user lookup ─────────────────────────────────────────────────────
    user_id = request.headers.get("user-id")
    if not user_id:
        return Response({"error": "user-id header is required."}, status=400)

    try:
        user = Users.objects.select_related("profile_id").get(user_id=user_id)
    except Users.DoesNotExist:
        return Response({"error": "User not found."}, status=404)

    if user.profile_status != "ACTIVATED":
        return Response({"error": "Account is not active."}, status=403)
    

    # ── Request params ─────────────────────────────────────────────────────────
    try:
        page      = int(request.data.get("page", 1))
        serial_no = int(request.data.get("serial_no", 1))
    except (ValueError, TypeError):
        page, serial_no = 1, 1

    if serial_no < 1 or serial_no > PAGE_SIZE:
        return Response(
            {"error": f"serial_no must be between 1 and {PAGE_SIZE}"}, status=400
        )

    feed_filter = str(request.data.get("filter", "all")).lower().strip()
    if feed_filter not in VALID_FILTERS:
        return Response(
            {"error": f"Invalid filter. Valid options: {', '.join(sorted(VALID_FILTERS))}."},
            status=400,
        )

    search_term  = request.data.get("search_term", "").strip()
    user_profile = user.profile_id

    # ── Base queryset: active products, excluding own ──────────────────────────
    base_qs = _active_products_qs(exclude_user_id=user_id)

    # ── User interest scores ───────────────────────────────────────────────────
    category_scores, product_scores = _get_track_stats(user)

    # ── Connection farmer IDs ──────────────────────────────────────────────────
    connection_farmer_ids = set(_get_connection_farmer_ids(user))

    # ── Build & rank product list ──────────────────────────────────────────────
    if search_term:
        # Step 1: multi-word search → sorted by match_count (most relevant first)
        search_results = _search_products(
            search_term, user_profile, base_qs,
            user, category_scores, product_scores,
            connection_farmer_ids,
        )

        # Step 2: apply expiry gate only — do NOT re-rank by score.
        # Re-ranking by score would destroy the match_count ordering.
        # Near-expiry local products still get injected at slot [1].
        ranked, ratings_map, sold_map = _apply_search_expiry_gate(
            search_results,
            user_profile,
            connection_farmer_ids,
        )

    else:
        if feed_filter == "connectiononly":
            ranked, ratings_map, sold_map = _feed_connection_only(
                user, user_profile, base_qs, category_scores, product_scores
            )
        elif feed_filter == "nearme":
            ranked, ratings_map, sold_map = _feed_near_me(
                user_profile, base_qs, category_scores, product_scores
            )
        else:  # "all"
            ranked, ratings_map, sold_map = _feed_all(
                user, user_profile, base_qs, category_scores, product_scores,
                connection_farmer_ids=connection_farmer_ids,
            )

    # ── Paginate & return single product ──────────────────────────────────────
    total_products = len(ranked)
    total_pages    = max(1, (total_products + PAGE_SIZE - 1) // PAGE_SIZE)
    absolute_index = (page - 1) * PAGE_SIZE + (serial_no - 1)

    if absolute_index >= total_products:
        return Response({"error": "No more products available."}, status=404)

    product  = ranked[absolute_index]
    has_more = absolute_index < total_products - 1

    return Response(
        {
            "page":        page,
            "serial_no":   serial_no,
            "total_pages": total_pages,
            "has_more":    has_more,
            "filter":      feed_filter,
            "product":     _serialize_product(product, ratings_map, sold_map),
        },
        status=200,
    )