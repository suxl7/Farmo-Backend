from backend.permissions import HasValidTokenForUser, IsFarmer, IsAdmin
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.models import Users, Product, FarmProducts
from backend.utils.media_handler import FileManager
from django.db.models import Q  
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.permissions import AllowAny
#import mimetypes
import json
import secrets

##########################################################################################
#                            Add Product Start
##########################################################################################

@api_view(['POST'])
#@permission_classes([AllowAny])
@permission_classes([HasValidTokenForUser, IsFarmer])
def add_products(request):
    user_id = request.headers.get('user-id')
    pid, response = handle_product_creation(user_id, request.data, request.FILES.getlist('media_files'))
    return response


@api_view(['POST'])
@permission_classes([HasValidTokenForUser, IsAdmin])
def add_product_FromAdmin(request):
    user_id = request.data.get('user_id')
    response = handle_product_creation(user_id, request.data, request.FILES.getlist('media_files'))
    return response


def handle_product_creation(user_id, data, media_files):
    name = data.get('name')
    category = data.get('category')
    is_organic = data.get('is_organic')
    quantity_available = data.get('quantity_available')
    cost_per_unit = data.get('cost_per_unit')
    discount_type = data.get('discount_type')
    discount = data.get('discount')
    produced_date_str = data.get('produced_date')
    expired_at = data.get('expired_at')
    description = data.get('description')
    delivery_option = data.get('delivery_option')

    produced_date = parse_date(produced_date_str)
    expiry_Date = timezone.now().date() + timezone.timedelta(days=int(expired_at))

    if not all([name, category, quantity_available, is_organic, cost_per_unit, produced_date, expiry_Date, delivery_option]):
        return None, Response({'error': 'Required fields are missing.'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate media files
    photos = [f for f in media_files if f.content_type.startswith('image/')]
    videos = [f for f in media_files if f.content_type.startswith('video/')]

    if len(photos) == 0:
        return None, Response({'error': 'At least one photo is required'}, status=status.HTTP_400_BAD_REQUEST)
    elif len(photos) > 3:
        return None, Response({'error': 'Maximum 3 photos allowed'}, status=status.HTTP_400_BAD_REQUEST)

    if len(videos) > 1:
        return None, Response({'error': 'Maximum 1 video allowed'}, status=status.HTTP_400_BAD_REQUEST)

    # Save media files
    file_manager = FileManager(user_id)
    media_entries = []

    for photo in photos:
        result = file_manager.save_product_file(photo, None, 'img', max_size_mb=5)
        if result['success']:
            media_entries.append({
                'serial_no': len(media_entries) + 1,
                'media_url': result['file_url'],
                'media_type': 'img'
            })

    if videos:
        video = videos[0]
        result = file_manager.save_product_file(video, None, 'vid', max_size_mb=50)
        if result['success']:
            media_entries.append({
                'serial_no': len(media_entries) + 1,
                'media_url': result['file_url'],
                'media_type': 'vid'
            })

    # Create product
    created = False
    pid = None
    while not created:
        pid = secrets.token_hex(16).upper()
        created = Product.create_product(
            pid=pid,
            user_id=user_id,
            name=name,
            category=category,
            is_organic=is_organic,
            quantity_available=quantity_available,
            cost_per_unit=cost_per_unit,
            discount_type=discount_type,
            discount=discount,
            produced_date=produced_date,
            expiry_Date=expiry_Date,
            description=description,
            delivery_option=delivery_option,
            media_url=media_entries
        )

    return Response({'message': 'Product created successfully'}, status=status.HTTP_201_CREATED)

##########################################################################################
#                            Add Product End
##########################################################################################

##########################################################################################
#                            Check FarmProduct Category Start
##########################################################################################
@api_view(['POST'])
@permission_classes([AllowAny])
def all_available_categories(request):
    try:
        with open("backend/static/json/product-categories.json") as f:
            data = json.load(f)
    except FileNotFoundError:
        return Response({'categories': []}, status=status.HTTP_200_OK)

    return Response({'categories': data}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def available_farm_product_on_category(request):
    category = request.data.get('category')
    try:
        if category == None or category == "" or category.lower() == "all":
            framProduct = FarmProducts.objects.filter().order_by('id')
        else:
            framProduct = FarmProducts.objects.filter(category__icontains = category).order_by('id')
        data = []
        for p in framProduct:
            data.append({
                "id": p.id,
                "english_name": p.primary_name,
                "nepali_name": p.secondary_name,
            })
            
    except FarmProducts.DoesNotExist:
        return Response({}, status=status.HTTP_404_NOT_FOUND)
    return Response({"category":category,"farm_products":data},status=status.HTTP_200_OK)
##########################################################################################
#                            Check FarmProduct Category End
##########################################################################################

##########################################################################################
#                            Product Management Start
##########################################################################################

##########################################################################################
#                            Product Management End
##########################################################################################

##########################################################################################
#                            Product Management Start
##########################################################################################
##########################################################################################
#                            Product Management End
##########################################################################################
