from backend.models import ProductScore, Product, Users
from django.db.models import Sum


def track_product_view(user, product, score):
    """
    Track product view and update ProductScore.

    Each call adds `score` to the matching category entry for the user.

    Normalization:
        When the SUM of all the user's ProductScore.score values reaches
        or exceeds 10 000, every entry is proportionally scaled so that
        the total becomes exactly 100, preserving the relative weights.

        Example — before normalization (total = 10 000):
            fish     → 6000   →  60
            vegetable→ 3000   →  30
            grain    →  500   →   5
            fruit    →  500   →   5
                                ─────
                                 100  ✓
    """
    if not user or not product:
        return

    SCORE_CAP   = 10_000
    RESET_TOTAL = 100

    # ── Upsert the category entry ────────────────────────────────────────────
    if not product.product_type:
        return

    score_entry, _ = ProductScore.objects.get_or_create(
        user_id=user,
        product_catagory=product.product_type,
        farmProduct=None,          # category-level entry has no specific FarmProduct
        defaults={"score": 0},
    )
    score_entry.score = (score_entry.score or 0) + int(score)
    score_entry.save(update_fields=["score"])

    # ── Check total and normalize if needed ─────────────────────────────────
    all_entries = list(ProductScore.objects.filter(user_id=user))
    total = sum(e.score or 0 for e in all_entries)

    if total >= SCORE_CAP:
        # Proportionally scale every entry so the total becomes RESET_TOTAL.
        # Use integer division first, then give the remainder to the largest entry
        # so the total is exactly RESET_TOTAL (no floating-point drift).
        scaled = [(e, int((e.score or 0) * RESET_TOTAL / total)) for e in all_entries]

        # Remainder from integer rounding
        remainder = RESET_TOTAL - sum(s for _, s in scaled)

        # Add remainder to the entry with the highest score to minimise distortion
        scaled.sort(key=lambda x: x[0].score or 0, reverse=True)

        for i, (entry, new_score) in enumerate(scaled):
            entry.score = new_score + (remainder if i == 0 else 0)

        ProductScore.objects.bulk_update([e for e, _ in scaled], ["score"])
