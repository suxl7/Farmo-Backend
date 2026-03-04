from backend.permissions import HasValidTokenForUser, IsFarmer, IsAdmin
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.models import Users, Product, FarmProducts, UserActivity, ProductRating, OrderRequest
from backend.serializers import ProductSerializer
from backend.utils.media_handler import FileManager
from django.db.models import Q  
from django.utils import timezone
from datetime import timedelta
from django.utils.dateparse import parse_date
from rest_framework.permissions import AllowAny
#import mimetypes
import json
import secrets

##########################################################################################
#                            Add Product Start
##########################################################################################

@api_view(['POST'])
@permission_classes([AllowAny, IsFarmer])
def add_products(request):
    """
    Create a new product with JSON data only (no media upload).
    Media should be uploaded separately via BigFileTransferHandler.
    """
    user_id = request.headers.get('user-id')
    print(user_id)
    response = handle_product_creation(user_id, request.data)
    return response


@api_view(['POST'])
@permission_classes([AllowAny, IsAdmin])
def add_product_FromAdmin(request):
    """
    Create a new product as admin with JSON data only (no media upload).
    Media should be uploaded separately via BigFileTransferHandler.
    """

    user_id = request.data.get('user_id')
    response = handle_product_creation(user_id, request.data)
    return response


def handle_product_creation(user_id, data):
        print(1)
        name             = data.get('product_name')
        product_type     = data.get('product_type')   # ✅ renamed from category
        is_organic       = data.get('is_organic')
        product_unit     = data.get('unit')
        quantity_available = data.get('quantity')
        cost_per_unit    = data.get('cost_per_unit')
        discount_type    = data.get('discount_type')
        discount         = data.get('discount')
        produced_date_str = data.get('produced_date')
        expired_at       = data.get('expiry_date')
        description      = data.get('description')
        delivery_option  = data.get('delivery_options')
        product_type     = data.get('product_type')
        keywords        = data.get('keywords')

        produced_date = parse_date(produced_date_str) if produced_date_str else None

        

        print(2)
        # ── Validate required fields ──────────────────────────────────────────
        required = {
            'name': name,
            'product_type': product_type,
            'quantity_available': quantity_available,
            'cost_per_unit': cost_per_unit,
            'produced_date': produced_date,
            'expiry_Date': expired_at,
            'product_unit': product_unit,
            'delivery_option': delivery_option,
            'discount_type': discount_type
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            return Response({
                'error': 'Required fields are missing.',
                'missing_fields': missing
            }, status=status.HTTP_400_BAD_REQUEST)

     # 1. Ensure the category exists first
        # If 'grain' doesn't exist, it creates it. If it does, it just retrieves it.
      
        product_type = update_category_file(product_type=product_type)

        if keywords:
            for keyword in keywords:
                clean_kw = keyword.strip().lower()

                exists = FarmProducts.objects.filter(
                    Q(category=product_type) &
                    (Q(primary_name=clean_kw) | Q(secondary_name=clean_kw))
                ).exists()

                if not exists:
                    from django.db.models import Max

                    max_id = FarmProducts.objects.aggregate(Max('id'))['id__max']

                    FarmProducts.objects.create(
                        id = max_id + 1,
                        primary_name=clean_kw,
                        secondary_name=clean_kw,
                        category=product_type
                    )
                    


        # ── Resolve user ──────────────────────────────────────────────────────
        try:
            user = Users.objects.get(user_id=user_id)
        except Users.DoesNotExist:
            return Response({'error': 'Invalid user-id'}, status=status.HTTP_404_NOT_FOUND)

        print(3)
        # ── Create product ────────────────────────────────────────────────────
        product = Product.create_product(
            user=user,
            name=name,
            product_type=product_type,   # ✅ fixed
            is_organic=is_organic,
            quantity_available=quantity_available,
            cost_per_unit=cost_per_unit,
            discount_type=discount_type,
            discount=discount,
            product_unit=product_unit,
            description=description,
            delivery_option=delivery_option,
            keywords=keywords
        )

        UserActivity.create_activity(user, activity="ADD_PRODUCT", discription="")
        print(5)
        return Response({
            'message': 'Product created successfully',
            'product_id': product.p_id,
            'note': 'Upload media files using BigFileTransferHandler with this product_id',
            'upload_instructions': {
                'subject': 'PRODUCT_MEDIA',
                'product_id': product.p_id,
                'file_purpose': 'img or vid',
            }
        }, status=status.HTTP_201_CREATED)


import json

def update_category_file(product_type):
    # Read JSON file
    filename = "backend/static/json/product-categories.json"
    with open(filename, "r") as f:
        data = json.load(f)

    if "-" not in product_type:
        key = product_type.strip().lower().replace(" ", "-")
    else:
        key = product_type


 # Format label
    # Check if product_type exists
    exists = any(item["key"] == key for item in data)

    if not exists:
        # Add new entry
        data.append({"key": key, "label": product_type})

        # Write back to file (pretty format)
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

    print(4)  
    print("from add product")
    return key

# Example usage

##############################################################################################
##############################################################################################

@api_view(['PUT'])
@permission_classes([HasValidTokenForUser, IsFarmer])
def update_product(request, pid):
    """
    Update product information (JSON data only, not media).
    
    To update media, use BigFileTransferHandler for upload or 
    delete_product_media endpoint for removal.
    """
    user_id = request.headers.get('user-id')
    
    try:
        product = Product.objects.get(pid=pid, user_id__user_id=user_id)
    except Product.DoesNotExist:
        return Response({
            'error': 'Product not found or you do not have permission to modify it'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Update allowed fields
    updatable_fields = [
        'name', 'category', 'is_organic', 'quantity_available', 
        'cost_per_unit', 'discount_type', 'discount', 'description', 
        'delivery_option', 'produced_date', 'expiry_Date'
    ]
    
    for field in updatable_fields:
        if field in request.data:
            setattr(product, field, request.data[field])
    
    product.save()
    
    return Response({
        'message': 'Product updated successfully',
        'product_id': pid
    }, status=status.HTTP_200_OK)

##############################################################################################
##############################################################################################

@api_view(['DELETE'])
@permission_classes([HasValidTokenForUser, IsFarmer])
def delete_product_media(request, pid):
    """
    Delete a specific media file from product.
    
    Request body should contain:
    - serial_no: The serial number of the media to delete
    """
    from backend.utils.media_handler import FileManager
    
    user_id = request.headers.get('user-id')
    serial_no = request.data.get('serial_no')
    
    if serial_no is None:
        return Response({
            'error': 'serial_no is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        product = Product.objects.get(pid=pid, user_id__user_id=user_id)
    except Product.DoesNotExist:
        return Response({
            'error': 'Product not found or you do not have permission to modify it'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serial_no = int(serial_no)
    current_media = product.media_url or []
    
    # Find media to remove
    media_to_remove = next((m for m in current_media if m['serial_no'] == serial_no), None)
    
    if not media_to_remove:
        return Response({
            'error': f'Media with serial_no {serial_no} not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check if it's the last photo
    remaining_photos = [m for m in current_media if m['media_type'] == 'img' and m['serial_no'] != serial_no]
    if media_to_remove['media_type'] == 'img' and len(remaining_photos) == 0:
        return Response({
            'error': 'Cannot remove last photo. At least one photo is required.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Delete file using FileManager
    file_manager = FileManager(user_id)
    file_url = media_to_remove.get('media_url', '')
    file_name = file_url.split('/')[-1] if file_url else None
    
    if file_name:
        delete_result = file_manager.delete_file('product', file_name)
        if not delete_result['success']:
            return Response({
                'error': f'Failed to delete file: {delete_result.get("error")}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Update product
    updated_media = [m for m in current_media if m['serial_no'] != serial_no]
    product.media_url = updated_media
    product.save()
    
    return Response({
        'message': 'Media file removed successfully',
        'removed_serial_no': serial_no,
        'remaining_count': len(updated_media)
    }, status=status.HTTP_200_OK)
\
##############################################################################################
##############################################################################################

@api_view(['GET'])
@permission_classes([HasValidTokenForUser])
def get_product_media_count(request, pid):
    """
    Get count of media files for a product.
    Useful to determine if more media can be added.
    """
    user_id = request.headers.get('user-id')
    
    try:
        product = Product.objects.get(pid=pid, user_id__user_id=user_id)
    except Product.DoesNotExist:
        return Response({
            'error': 'Product not found or you do not have permission to view it'
        }, status=status.HTTP_404_NOT_FOUND)
    
    current_media = product.media_url or []
    photos = [m for m in current_media if m['media_type'] == 'img']
    videos = [m for m in current_media if m['media_type'] == 'vid']
    
    return Response({
        'product_id': pid,
        'total_media': len(current_media),
        'photos': len(photos),
        'videos': len(videos),
        'can_add_photos': len(photos) < 3,
        'can_add_videos': len(videos) < 1,
        'media_list': current_media
    }, status=status.HTTP_200_OK)




##########################################################################################
#                            Add Product End
##########################################################################################

##########################################################################################
#                            Check FarmProduct Category Start
##########################################################################################
@api_view(['POST'])
@permission_classes([AllowAny])
def all_available_categories(request):
    search = request.data.get('search', '').strip().lower()
    try:
        with open("backend/static/json/product-categories.json") as f:
            data = json.load(f)
    except FileNotFoundError:
        return Response({'categories': []}, status=status.HTTP_200_OK)

    # If search is provided, filter categories
    if search:
        filtered = [
            item for item in data
            if search in item.get("key", "").lower() or search in item.get("label", "").lower()
        ]
    else:
        filtered = data

    return Response({'categories': filtered}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def available_farm_product_on_category(request):
    category = request.data.get('category')
    keyword = request.data.get('keyword', '').strip()

    try:
        # Base queryset
        if not category or category.lower() == "all":
            farm_products = FarmProducts.objects.all().order_by('id')
        else:
            farm_products = FarmProducts.objects.filter(
                category__icontains=category
            ).order_by('id')

        # Apply keyword filter if provided
        if keyword:
            farm_products = farm_products.filter(
                primary_name__icontains=keyword
            ) | farm_products.filter(
                secondary_name__icontains=keyword
            )

        data = [
            {
                "id": p.id,
                "english_name": p.primary_name,
                "nepali_name": p.secondary_name,
            }
            for p in farm_products
        ]

    except FarmProducts.DoesNotExist:
        return Response({}, status=status.HTTP_404_NOT_FOUND)

    return Response(
        {"category": category, "farm_products": data},
        status=status.HTTP_200_OK
    )

##########################################################################################
#                            Check FarmProduct Category End
##########################################################################################

##########################################################################################
#                            Product Management Start
##########################################################################################
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from collections import defaultdict

from backend.models import Users, Product, Connections, ProductScore, FarmProducts
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Avg


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
PAGE_SIZE          = 10
EXPIRY_RADIUS_DAYS = 30   # ≤ 30 days left  → local (same municipal)
EXPIRY_WIDE_DAYS   = 90   # ≤ 90 days left  → district radius
                           # > 90 days left  → province/country radius

VALID_FILTERS = {"all", "connectiononly", "nearme"}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _serialize_product(product: Product) -> dict:
    """Convert a Product ORM object to the API response shape."""
    today = timezone.now().date()

    if product.product_status == "Sold":
        status = "out_of_stock"
    elif product.expiry_Date and product.expiry_Date <= today:
        status = "inactive"
    elif product.quantity_available <= 0:
        status = "out_of_stock"
    else:
        status = "active"

    media = product.media_url or []
    if isinstance(media, dict):
        media = list(media.values())
    image = media[0] if media else ""
    rating = ProductRating.objects.filter(p_id=product).aggregate(
        avg_rating=Avg('score')
    )['avg_rating'] or 0.0

    return {
        "id":        product.p_id,
        "name":      product.name,
        "product_type":  product.product_type,       # ✅ fixed
        "status":    status,
        "discount_type": product.discount_type,
        "discount":  str(product.discount),
        "is_organic": product.is_organic,
        "price":     str(product.cost_per_unit),
        "priceUnit": "Rs.",
        "stock":     str(product.quantity_available),
        "stockUnit": product.product_unit.lower(),
        "image":     image,
        "rating":   str(rating),
    }


def _active_products_qs():
    """Base queryset: only Available, in-stock, non-expired products."""
    today = timezone.now().date()
    return Product.objects.filter(
        product_status="Available",
        quantity_available__gt=0,
    ).filter(
        Q(expiry_Date__isnull=True) | Q(expiry_Date__gt=today)
    )


def _get_connection_farmer_ids(user: Users) -> list:
    """Return user_ids of ACCEPTED connections where the target is a Farmer/VerifiedFarmer."""
    accepted = Connections.objects.filter(
        user=user, status="ACCEPTED"
    ).select_related("target_user__profile_id")

    return [
        conn.target_user.user_id
        for conn in accepted
        if conn.target_user.profile_id.user_type in ("Farmer", "VerifiedFarmer")
    ]


def _get_track_stats(user: Users):
    """
    Returns:
        category_scores – {category_slug: total_score}
        product_scores  – {farm_product_id: total_score}
    """
    tracks = ProductScore.objects.filter(user_id=user).select_related("farmProduct")
    category_scores = defaultdict(int)
    product_scores  = defaultdict(int)

    for t in tracks:
        score = t.score or 0
        if t.product_catagory:
            category_scores[t.product_catagory] += score
        if t.farmProduct_id:
            product_scores[t.farmProduct_id] += score

    return dict(category_scores), dict(product_scores)


def _products_from_connections(farmer_ids: list) -> list:
    """
    Pull products from connected farmers.
    Active (newest first) → inactive/sold pushed to bottom.
    """
    if not farmer_ids:
        return []

    today = timezone.now().date()
    qs = Product.objects.filter(
        user_id__in=farmer_ids
    ).exclude(product_status="Sold").select_related("user_id__profile_id")

    active = qs.filter(
        product_status="Available",
        quantity_available__gt=0,
    ).filter(
        Q(expiry_Date__isnull=True) | Q(expiry_Date__gt=today)
    ).order_by("-registered_at")

    inactive = qs.exclude(
        p_id__in=active.values_list("p_id", flat=True)
    ).order_by("-registered_at")

    return list(active) + list(inactive)


def _products_by_track(user: Users, category_scores: dict, product_scores: dict,
                       exclude_ids: set) -> list:
    """
    Products matching the user's tracked categories / farm-products.
    Ordered by descending score.
    """
    if not category_scores and not product_scores:
        return []

    base_qs = _active_products_qs().exclude(p_id__in=exclude_ids)
    ranked_categories = sorted(category_scores, key=category_scores.get, reverse=True)
    ranked_fp_ids     = sorted(product_scores,  key=product_scores.get,  reverse=True)

    seen    = set()
    ordered = []

    for fp_id in ranked_fp_ids:
        for prod in base_qs.filter(
            keywords__contains=[fp_id]
        ).order_by("-registered_at")[:20]:
            if prod.p_id not in seen:
                seen.add(prod.p_id)
                ordered.append(prod)

    for cat in ranked_categories:
        for prod in base_qs.filter(product_type=cat).order_by("-registered_at")[:20]:  # ✅ fixed
            if prod.p_id not in seen:
                seen.add(prod.p_id)
                ordered.append(prod)

    return ordered


def _products_by_location(user_profile, exclude_ids: set) -> list:
    """
    Geo-radius products sorted by expiry logic:
      - Short expiry (≤30d) → same municipal  (local urgency)
      - Medium expiry (≤90d) → same district
      - Long/no expiry       → same province
      - Nationwide fallback  → tools & equipment only
    """
    today      = timezone.now().date()
    base_qs    = _active_products_qs().exclude(p_id__in=exclude_ids)
    short_exp  = today + timedelta(days=EXPIRY_RADIUS_DAYS)
    medium_exp = today + timedelta(days=EXPIRY_WIDE_DAYS)

    local = base_qs.filter(
        user_id__profile_id__municipal=user_profile.municipal,
        expiry_Date__lte=short_exp,
        expiry_Date__gt=today,
    ).order_by("expiry_Date")

    district = base_qs.filter(
        user_id__profile_id__district=user_profile.district,
    ).filter(
        Q(expiry_Date__gt=short_exp, expiry_Date__lte=medium_exp) |
        Q(expiry_Date__isnull=True)
    ).exclude(
        p_id__in=local.values_list("p_id", flat=True)
    ).order_by("expiry_Date")

    province = base_qs.filter(
        user_id__profile_id__province=user_profile.province,
    ).filter(
        Q(expiry_Date__gt=medium_exp) | Q(expiry_Date__isnull=True)
    ).exclude(
        p_id__in=local.values_list("p_id", flat=True)
    ).exclude(
        p_id__in=district.values_list("p_id", flat=True)
    ).order_by("expiry_Date")

    nationwide = base_qs.filter(
        product_type="tool-equipment"                           # ✅ fixed
    ).exclude(
        p_id__in=local.values_list("p_id", flat=True)
    ).exclude(
        p_id__in=district.values_list("p_id", flat=True)
    ).exclude(
        p_id__in=province.values_list("p_id", flat=True)
    ).order_by("expiry_Date")

    return list(local) + list(district) + list(province) + list(nationwide)


def _merge_and_deduplicate(*lists) -> list:
    """Merge multiple product lists preserving order, removing duplicates."""
    seen   = set()
    merged = []
    for lst in lists:
        for product in lst:
            if product.p_id not in seen:
                seen.add(product.p_id)
                merged.append(product)
    return merged


def _paginate(items: list, page: int) -> tuple:
    """Returns (page_items, has_prev, has_next, total_pages). Page is 1-indexed."""
    total       = len(items)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page        = max(1, min(page, total_pages))
    start       = (page - 1) * PAGE_SIZE
    return (
        items[start: start + PAGE_SIZE],
        page > 1,
        page < total_pages,
        total_pages,
    )


# ─────────────────────────────────────────────
# FILTER STRATEGIES
# ─────────────────────────────────────────────

def _feed_all(user: Users, user_profile) -> list:
    """Full ranked feed: connections → tracked interests → location."""
    farmer_ids          = _get_connection_farmer_ids(user)
    connection_products = _products_from_connections(farmer_ids)
    seen_ids            = {p.p_id for p in connection_products}

    category_scores, product_scores = _get_track_stats(user)
    track_products = _products_by_track(user, category_scores, product_scores, seen_ids)
    seen_ids.update(p.p_id for p in track_products)

    location_products = _products_by_location(user_profile, seen_ids)

    return _merge_and_deduplicate(connection_products, track_products, location_products)


def _feed_connection_only(user: Users) -> list:
    """Only products from accepted farmer connections (active first, then inactive)."""
    farmer_ids = _get_connection_farmer_ids(user)
    return _products_from_connections(farmer_ids)


def _feed_near_me(user_profile) -> list:
    """Only location-based products; no connection or track filtering applied."""
    return _products_by_location(user_profile, exclude_ids=set())


# ─────────────────────────────────────────────
# MAIN VIEW
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def get_product_feed(request):
    """
    POST /api/product/feed/

    Headers:
        user-id   (required)

    Body (JSON):
        page    : int     – default 1
        filter  : str     – "all" | "connectiononly" | "nearme"   default "all"
        search_term : str

    Response:
    {
        "page":        1,
        "total_pages": 4,
        "prev_page":   false,
        "next_page":   true,
        "filter":      "all",
        "products":    [ { ...product fields... } ]
    }
    """

    # ── Auth / user lookup ───────────────────
    user_id = request.headers.get("user-id")
    if not user_id:
        return Response({"error": "user-id header is required."}, status=400)

    try:
        user = Users.objects.select_related("profile_id").get(user_id=user_id)
    except Users.DoesNotExist:
        return Response({"error": "User not found."}, status=404)

    if user.profile_status != "ACTIVATED":
        return Response({"error": "Account is not active."}, status=403)

    # ── Request params ───────────────────────
    try:
        page = int(request.data.get("page", 1))
    except (ValueError, TypeError):
        page = 1


    feed_filter = str(request.data.get("filter", "all")).lower().strip()
    if feed_filter not in VALID_FILTERS:
        return Response(
            {"error": f"Invalid filter. Valid options: {', '.join(sorted(VALID_FILTERS))}."},
            status=400,
        )

    user_profile = user.profile_id

    # ── Build product list based on chosen filter ─
    if feed_filter == "connectiononly":
        all_products = _feed_connection_only(user)

    elif feed_filter == "nearme":
        all_products = _feed_near_me(user_profile)

    else:  # "all"
        all_products = _feed_all(user, user_profile)

    # ── Apply search filter ──────────────────
    search_term = request.data.get("search_term", "").strip()
    if search_term:
        search_lower = search_term.lower()
        
        # Search in current filtered products
        filtered_products = [
            p for p in all_products 
            if search_lower in p.name.lower() 
            or (p.product_type and search_lower in p.product_type.lower())
        ]
        
        # If no results, expand search by location priority
        if not filtered_products:
            base_qs = _active_products_qs()
            
            # 1. Search in municipal
            local = base_qs.filter(
                user_id__profile_id__municipal=user_profile.municipal
            ).filter(
                Q(name__icontains=search_term) | Q(product_type__icontains=search_term)
            )
            filtered_products = list(local)
            
            # 2. If not found, search in district
            if not filtered_products:
                district = base_qs.filter(
                    user_id__profile_id__district=user_profile.district
                ).filter(
                    Q(name__icontains=search_term) | Q(product_type__icontains=search_term)
                )
                filtered_products = list(district)
            
            # 3. If not found, search in province
            if not filtered_products:
                province = base_qs.filter(
                    user_id__profile_id__province=user_profile.province
                ).filter(
                    Q(name__icontains=search_term) | Q(product_type__icontains=search_term)
                )
                filtered_products = list(province)
            
            # 4. If still not found, search nationwide
            if not filtered_products:
                nationwide = base_qs.filter(
                    Q(name__icontains=search_term) | Q(product_type__icontains=search_term)
                )
                filtered_products = list(nationwide)
        
        all_products = filtered_products
    
    # If less than PAGE_SIZE, fill with nearby products
    if len(all_products) < PAGE_SIZE:
        seen_ids = {p.p_id for p in all_products}
        filler = _products_by_location(user_profile, seen_ids)
        all_products.extend(filler[:PAGE_SIZE - len(all_products)])

    # ── Paginate ─────────────────────────────
    page_products, has_prev, has_next, total_pages = _paginate(all_products, page)

    # ── Serialize & respond ──────────────────
    return Response({
        "page":        page,
        "total_pages": total_pages,
        "prev_page":   has_prev,
        "next_page":   has_next,
        "filter":      feed_filter,
        "products":    [_serialize_product(p) for p in page_products],
    }, status=200)
##########################################################################################
#                            Product Management End
##########################################################################################

##########################################################################################
#                            Product see by admin Start
##########################################################################################
@api_view(['POST'])
@permission_classes([HasValidTokenForUser,IsAdmin])
def product_home_admin(request):
    try:
        product = Product.objects.all()
        Todays_product_list = product.filter(registered_at__date=timezone.now().date())
        Total_listed_product = product.count()
        Active_Product = product.filter(product_status="Available").count()
    except product.DoesnotExist:
        return Response({}, status=status.HTTP_404_NOT_FOUND)
    return Response({"todays_product_list": Todays_product_list,
                     "active_product": Active_Product,
                     "total_listed_product": Total_listed_product}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def product_filter_admin(request):
    from django.core.paginator import Paginator
    from django.db.models import Q, Avg, Sum

    search_term    = request.data.get('search_term')
    district       = request.data.get('district')
    farmer         = request.data.get('farmer')
    product_status = request.data.get('product_status')
    page_number    = request.data.get('page', 1)

    VALID_STATUSES = ['all', 'All', 'Available', 'Sold', 'Expired', 'Deleted']

    query = Q()

    # ── Search term ──────────────────────────────────────────────────────────
    if search_term:
        query &= Q(p_id__icontains=search_term) | Q(name__icontains=search_term)

    # ── Farmer ───────────────────────────────────────────────────────────────
    if farmer:                                   # ✅ only filter when farmer is non-empty
        query &= (
            Q(user_id__user_id__icontains=farmer)
            | Q(user_id__profile_id__f_name__icontains=farmer)
            | Q(user_id__profile_id__m_name__icontains=farmer)
            | Q(user_id__profile_id__l_name__icontains=farmer)
        )

    # ── District ─────────────────────────────────────────────────────────────
    if district and district.lower() not in ["all", "all districts"]:
        query &= Q(user_id__profile_id__district__icontains=district)

    # ── Product Status ───────────────────────────────────────────────────────
    if product_status:
        if product_status not in VALID_STATUSES:
            return Response(
                {"error": f"Invalid product_status. Choose from: {VALID_STATUSES}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if product_status.lower() != 'all':      # ✅ case-insensitive check
            query &= Q(product_status=product_status)

    # ── Query ─────────────────────────────────────────────────────────────────
    products  = Product.objects.filter(query).order_by('-registered_at')
    paginator = Paginator(products, 10)
    page_obj  = paginator.get_page(page_number)

    # ── Serialize ─────────────────────────────────────────────────────────────
    data = []
    for product in page_obj:
        rating = ProductRating.objects.filter(p_id=product).aggregate(Avg('score'))['score__avg']
        sales  = OrderRequest.objects.filter(product=product).aggregate(total=Sum('total_cost'))['total'] or 0

        data.append({
            "p_id":           product.p_id,
            "name":           product.name,
            "user_id":        product.user_id.user_id,
            "farmer":         product.user_id.get_full_name_from_userModel(),
            "product_type":   product.product_type,
            "rating":         round(rating, 1) if rating else None,
            "sales":          sales,
            "product_status": product.product_status,
        })

    return Response({
        "total_pages":    paginator.num_pages,
        "total_products": paginator.count,
        "current_page":   page_obj.number,
        "has_next":       page_obj.has_next(),
        "has_previous":   page_obj.has_previous(),
        "products":       data,
    }, status=status.HTTP_200_OK)
    

##########################################################################################
#                             Product see by admin End
##########################################################################################
##########################################################################################
#                             Product Details Start
##########################################################################################
@api_view(['POST'])
@permission_classes([AllowAny])
def product_details_for_users(request):
    from django.db.models import Avg, Count
    
    p_id = request.data.get('p_id')
    
    try:
        product = Product.objects.select_related('user_id__profile_id').get(p_id=p_id)
        farmer = product.user_id
        print(farmer.user_id)
        
        # Get rating stats
        rating_count = ProductRating.objects.filter(p_id=product).count()
        avg_rating = ProductRating.objects.filter(p_id=product).aggregate(Avg('score'))['score__avg']
        
        # Get sold count
        sold_count = OrderRequest.objects.filter(product=product, order_status='ACCEPTED').count()
        
        # Format sold count
        if sold_count >= 1000000:
            sold_count_str = f"{sold_count / 1000000:.1f}m".rstrip('0').rstrip('.')
        elif sold_count >= 1000:
            sold_count_str = f"{sold_count / 1000:.1f}k".rstrip('0').rstrip('.')
        else:
            sold_count_str = str(sold_count)
        
        # Get media count
        media_list = product.media_url or []
        
        data = {
            "p_id": product.p_id,
            "user_id": product.user_id.user_id,
            "name": product.name,
            "product_type": product.product_type,
            "keywords": product.keywords or [],
            "is_organic": product.is_organic,
            "product_status": product.product_status.lower(),
            "Cost_per_unit": str(product.cost_per_unit),
            "Unit": product.product_unit.lower(),
            "in_Stock": product.quantity_available > 0,
            "discount_type": product.discount_type or None,
            "discount_value": str(product.discount) if product.discount else None,
            "description": product.description,
            "registered_date": product.registered_at.strftime("%d-%m-%Y"),
            "produced_date": product.produced_date.strftime("%d-%m-%Y"),
            "expiry_date": product.expiry_Date.strftime("%d-%m-%Y") if product.expiry_Date else None,
            "rating": round(avg_rating, 1) if avg_rating else 0,
            "rating_count": rating_count,
            "sold_count": sold_count_str,
            "farmer_name": farmer.get_full_name_from_userModel(),
            "farmer_location": f"{farmer.profile_id.municipal}-{product.user_id.profile_id.ward}, {product.user_id.profile_id.district}",
            "no_of_media": len(media_list),
        }
        
        return Response(data, status=status.HTTP_200_OK)
        
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
##########################################################################################
#                             Product Details End
##########################################################################################
