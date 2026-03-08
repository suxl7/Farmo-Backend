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
   
        name             = data.get('product_name')
        product_type     = data.get('product_type')   # ✅ renamed from category
        is_organic       = data.get('is_organic', False)
        product_unit     = data.get('unit')
        quantity_available = data.get('quantity')
        cost_per_unit    = data.get('cost_per_unit')
        discount_type    = data.get('discount_type')
        discount         = data.get('discount')
        produced_date_str = data.get('produced_date')
        expired_at = parse_date(data.get('expiry_date')) if data.get('expiry_date') else None
        description      = data.get('description')
        delivery_option  = data.get('delivery_options')
        product_type     = data.get('product_type')
        keywords        = data.get('keywords')
        print(data)
        produced_date = parse_date(produced_date_str) if produced_date_str else None

        if str(delivery_option).lower() not in ['available']:
            delivery_option = 'Not-Available'
        
        product_unit = str(product_unit).lower()

        match product_unit:
            case "kg" | "kilogram":
                product_unit = "kg"
            case "g" | "gram":
                product_unit = "g"
            case "l" | "litre":
                product_unit = "l"
            case "ml" | "millilitre":
                product_unit = "ml"
            case "pcs" | "piece":
                product_unit = "pcs"
            case _:
                # default case
                product_unit = product_unit

        
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
            produced_date=produced_date,
            expiry_Date=expired_at,
            description=description,
            delivery_option=delivery_option,
            keywords=keywords
        )

        print("Add Product Succesful")
        UserActivity.create_activity(user, activity="ADD_PRODUCT", discription="")
        
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
    return key

# Example usage

##############################################################################################
##############################################################################################

@api_view(['GET'])
@permission_classes([AllowAny, IsFarmer])
def get_product_for_update(request, pid):
    """
    Get product data for updating.
    """
    user_id = request.headers.get('user-id')
    #p_id = request.data.get('p_id')
    
    try:
        product = Product.objects.get(p_id=pid, user_id__user_id=user_id)
    except Product.DoesNotExist:
        return Response({
            'error': 'Product not found or you do not have permission to view it'
        }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'name': product.name,
        'product_type': product.product_type,
        'is_organic': product.is_organic,
        'quantity_available': str(product.quantity_available),
        'cost_per_unit': str(product.cost_per_unit),
        'discount_type': product.discount_type,
        'discount': str(product.discount) if product.discount else None,
        'expiry_Date': product.expiry_Date.strftime('%Y-%m-%d') if product.expiry_Date else None,
        'description': product.description,
        'delivery_option': product.delivery_option,
        'keywords': product.keywords or []
    }, status=status.HTTP_200_OK)

##############################################################################################
##############################################################################################

@api_view(['PUT'])
@permission_classes([AllowAny, IsFarmer])
def update_product(request):
    """
    Update product information (JSON data only, not media).
    
    To update media, use BigFileTransferHandler for upload or 
    delete_product_media endpoint for removal.
    """
    user_id = request.headers.get('user-id')
    pid = request.data.get('p_id')

    try:
        product = Product.objects.get(p_id=pid, user_id__user_id=user_id)
    except Product.DoesNotExist:
        return Response({
            'error': 'Product not found or you do not have permission to modify it'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Normalize delivery_option
    if 'delivery_option' in request.data:
        delivery_value = str(request.data.get('delivery_option')).lower().replace(' ', '').replace('_', '')
        if delivery_value in ['notavailable', 'not-available']:
            request.data['delivery_option'] = 'Not-Available'
    
    # Update allowed fields
    updatable_fields = [
        'name', 'product_type', 'is_organic', 'quantity_available',
        'cost_per_unit', 'discount_type', 'discount', 'description', 
        'delivery_option', 'expiry_Date'
    ]
    
    for field in updatable_fields:
        if field in request.data:
            value = request.data[field]
            # Normalize discount_type to match constraint: '', 'None', 'Percentage', 'Fixed', 'Flat'
            if field == 'discount_type' and value:
                value = value.capitalize() if value.lower() in ['percentage', 'fixed', 'flat'] else value
            setattr(product, field, value)
    
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
        product = Product.objects.get(p_id=pid, user_id__user_id=user_id)
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
        product = Product.objects.get(p_id=pid, user_id__user_id=user_id)
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
    # print(product_status)

    VALID_STATUSES = ['all', 'All', 'Available', 'Sold', 'Expired', 'Deleted', 'Not-Available', 'Not Available']

    query = Q()

    # ── Search term ──────────────────────────────────────────────────────────
    if search_term:
        query &= Q(p_id__icontains=search_term) | Q(name__icontains=search_term)

    # ── Farmer ───────────────────────────────────────────────────────────────
    if farmer:
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
        status_lower = product_status.lower().replace('_', '-').replace(' ', '-')
        if status_lower != 'all':
            query &= Q(product_status='Not-Available') if status_lower == 'not-available' else Q(product_status=product_status)

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
    from backend.utils.score_tracker import track_product_view
    
    p_id = request.data.get('p_id')
    user_id = request.headers.get('user-id')
    
    try:
        product = Product.objects.select_related('user_id__profile_id').get(p_id=p_id)
        farmer = product.user_id
        
        # Track view if user is not the owner
        if user_id and user_id != farmer.user_id:
            try:
                user = Users.objects.get(user_id=user_id)
                track_product_view(user, product, 2)
            except Users.DoesNotExist:
                pass
        
        # Get rating stats
        rating_count = ProductRating.objects.filter(p_id=product).count()
        avg_rating = ProductRating.objects.filter(p_id=product).aggregate(Avg('score'))['score__avg']
        
        # Get sold count
        sold_count = OrderRequest.objects.filter(product=product, order_status='DELIVERED').count()
        
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
            "produced_date": product.produced_date.strftime("%d-%m-%Y") if product.produced_date else None,
            "expiry_date": product.expiry_Date.strftime("%d-%m-%Y") if product.expiry_Date else None,
            "rating": round(avg_rating, 1) if avg_rating else 0,
            "rating_count": rating_count,
            "sold_count": sold_count_str,
            "farmer_name": farmer.get_full_name_from_userModel(),
            "farmer_location": f"{farmer.profile_id.municipal}-{product.user_id.profile_id.ward}, {product.user_id.profile_id.district}",
            "no_of_media": len(media_list),
            "delivery_option": product.delivery_option
        }
    
        
        return Response(data, status=status.HTTP_200_OK)
        
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
##########################################################################################
#                             Product Details End
##########################################################################################
##########################################################################################
#                             My Product List start
##########################################################################################
@api_view(['POST'])
@permission_classes([AllowAny, IsFarmer])
def my_product_list(request):
    from django.core.paginator import Paginator
    from datetime import datetime
    from django.db.models import Avg
    
    user_id = request.headers.get('user-id')
    filter_status = request.data.get('filter', 'all')
    page = request.data.get('page', 1)
    search_for = request.data.get('search', '')
    date_from = request.data.get('date_from', None)
    date_to = request.data.get('date_to', None)
    sort_by = request.data.get('sort_by', 'newest')
    # print(filter_status)
    if str(filter_status).lower() not in ['all', 'available', 'sold', 'expired', 'deleted', 'not-available', 'not available']:
        return Response({'error': 'Invalid filter'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = Users.objects.get(user_id=user_id)
        query = Q(user_id=user)
        
        # Exclude deleted products unless filter is 'deleted'
        if str(filter_status).lower() == 'deleted':
            query &= Q(product_status__iexact='deleted')
        elif str(filter_status).lower() == 'all':
            query &= ~Q(product_status__iexact='deleted')
        else:
            query &= Q(product_status__iexact=filter_status)
        
        if search_for:
            query &= (Q(name__icontains=search_for) | Q(p_id__icontains=search_for) | Q(product_type__icontains=search_for))
        
        if date_from and date_to:
            date_from_obj = datetime.strptime(date_from, '%d-%m-%Y')
            date_to_obj = datetime.strptime(date_to, '%d-%m-%Y')
            query &= Q(registered_at__date__range=(date_from_obj.date(), date_to_obj.date()))
        
        products = Product.objects.filter(query)
        
        if sort_by == 'oldest':
            products = products.order_by('registered_at')
        elif sort_by == 'price_low':
            products = products.order_by('cost_per_unit')
        elif sort_by == 'price_high':
            products = products.order_by('-cost_per_unit')
        elif sort_by == 'name':
            products = products.order_by('name')
        else:
            products = products.order_by('-registered_at')
        
        paginator = Paginator(products, 50)
        page_obj = paginator.get_page(page)
        
        data = []
        for p in page_obj:
            rating = ProductRating.objects.filter(p_id=p).aggregate(Avg('score'))['score__avg']
            sold_count = OrderRequest.objects.filter(product=p, order_status='DELIVERED').count()
            
            data.append({
                "p_id": p.p_id,
                "name": p.name,
                "product_type": p.product_type,
                "cost_per_unit": str(p.cost_per_unit),
                "quantity_available": str(p.quantity_available),
                "product_status": p.product_status,
                "registered_at": p.registered_at.strftime('%d-%m-%Y'),
                "rating": round(rating, 1) if rating else 0,
                "sold_count": sold_count
            })
        
        return Response({
            "total_pages": paginator.num_pages,
            "total_products": paginator.count,
            "current_page": page_obj.number,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "products": data
        }, status=status.HTTP_200_OK)
        
    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
##########################################################################################
#                             My Product List End
##########################################################################################
##########################################################################################
#                             My Product Available/Not-Available Start
##########################################################################################
@api_view(['POST'])
@permission_classes([AllowAny, IsFarmer])
def product_availability_toggle(request):
    user_id = request.headers.get('user-id')
    p_id = request.data.get('p_id')
    action = request.data.get('action')  # 'available' or 'not_available'

    try:
        user = Users.objects.get(user_id=user_id)
        product = Product.objects.get(p_id=p_id, user_id=user)

        if str(action).lower() == 'available' and product.product_status == 'Not-Available':
            product.product_status = 'Available'
        elif str(action).lower() in ['not_available', 'not available', 'not-available'] and product.product_status == 'Available':
            product.product_status = 'Not-Available'
        else:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

        product.save()

        return Response({'message': f'Product status updated to {action}'}, status=status.HTTP_200_OK)

    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

##########################################################################################
#                             My Product Available/Not-Available End
##########################################################################################
