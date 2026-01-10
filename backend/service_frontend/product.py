from backend.permissions import HasValidTokenForUser, IsFarmer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.models import Users, Product, ProductMedia
from backend.utils.media_handler import FileManager
from django.db.models import Q  
from django.utils import timezone
from django.utils.dateparse import parse_date
#import mimetypes
import secrets



@api_view(['POST'])
@permission_classes([HasValidTokenForUser, IsFarmer])
def add_products(request):
    """Protected view - requires valid token"""
    user = request.header.get('user_id')
    name = request.data.get('name')
    category = request.data.get('category')
    is_organic = request.data.get('is_organic')
    quantity_available = request.data.get('quantity_available')
    cost_per_unit = request.data.get('cost_per_unit')
    produced_date_str = request.data.get('produced_date')
    expired_at = request.data.get('expired_at')
    description = request.data.get('description')
    delivery_option = request.data.get('delivery_option')
    
    media_files = request.FILES.getlist('media_files')

    produced_date = parse_date(produced_date_str)
    expiry_Date = timezone.now().date() + timezone.timedelta(days=expired_at)

    if not all([name, category, quantity_available, is_organic, cost_per_unit, produced_date, expiry_Date, delivery_option]):
        return Response({
            'error': 'Required fields are missing.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate media files
    photos = [f for f in media_files if f.content_type.startswith('image/')]
    videos = [f for f in media_files if f.content_type.startswith('video/')]
    
    if len(photos) > 3:
        return Response({'error': 'Maximum 3 photos allowed'}, status=status.HTTP_400_BAD_REQUEST)
    
    if len(videos) > 1:
        return Response({'error': 'Maximum 1 video allowed'}, status=status.HTTP_400_BAD_REQUEST)
    
    created = False
    while not created:
        pid = secrets.token_hex(16).upper()
        created = Product.create_product(
            pid=pid,
            user_id=user,
            name=name,
            category=category,
            is_organic=is_organic,
            quantity_available=quantity_available,
            cost_per_unit=cost_per_unit,
            produced_date=produced_date,
            expiry_Date=expiry_Date,
            description=description,
            delivery_option=delivery_option
        )
    
    # Save media files
    file_manager = FileManager(user.user_id)
    #product_obj = Product.objects.get(P_id=pid)
    
    for photo in photos:
        result = file_manager.save_product_file(photo, pid, 'img', max_size_mb=5)
        if result['success']:
            while  created:
                created = ProductMedia.create_media(pid, result['file_url'], 'image')
    
    for video in videos:
        result = file_manager.save_product_file(video, pid, 'vid', max_size_mb=50)
        if result['success']:
            while  created:
                created = ProductMedia.create_media(pid, result['file_url'], 'video')
    
    return Response({
        'message': 'Product created successfully',
        'product_id': pid
    }, status=status.HTTP_201_CREATED)
