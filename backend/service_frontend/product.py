from backend.permissions import HasValidTokenForUser, IsFarmer, IsAdmin
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.models import Users, Product, FarmProducts, UserActivity
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
@permission_classes([AllowAny])
def add_products(request):
    """
    Create a new product with JSON data only (no media upload).
    Media should be uploaded separately via BigFileTransferHandler.
    """
    user_id = request.headers.get('user-id')
    response = handle_product_creation(user_id, request.data)
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def add_product_FromAdmin(request):
    """
    Create a new product as admin with JSON data only (no media upload).
    Media should be uploaded separately via BigFileTransferHandler.
    """
    user_id = request.data.get('user_id')
    response = handle_product_creation(user_id, request.data)
    return response


def handle_product_creation(user_id, data):
    """
    Handle product creation with JSON data only.
    Media files must be uploaded separately through BigFileTransferHandler.
    """
    try:
        # Extract product data
        name = data.get('name')
        category = data.get('category')
        is_organic = data.get('is_organic', False)
        quantity_available = data.get('quantity_available')
        cost_per_unit = data.get('cost_per_unit')
        discount_type = data.get('discount_type')
        discount = data.get('discount')
        produced_date_str = data.get('produced_date')
        expired_at = data.get('expired_at')
        description = data.get('description')
        delivery_option = data.get('delivery_option')

        # Parse produced_date
        produced_date = parse_date(produced_date_str) if produced_date_str else None

        # Calculate expiry date from "expired_at" days
        expiry_Date = None
        produced_date = parse_date(data.get('produced_date'))

        if produced_date and expired_at:
            try:
                expiry_days = int(expired_at)
                expiry_Date = produced_date + timedelta(days=expiry_days)
            except ValueError:
                expiry_Date = None  # invalid input, leave empty
        # Validate required fields
        required = [name, category, quantity_available, cost_per_unit, produced_date, expiry_Date, delivery_option]
        if not all(required):
            return Response({
                'error': 'Required fields are missing.',
                'required_fields': ['name', 'category', 'quantity_available', 'is_organic',
                                    'cost_per_unit', 'produced_date', 'expired_at', 'delivery_option']
            }, status=status.HTTP_400_BAD_REQUEST)

        # Resolve user
        try:
            user = Users.objects.get(user_id=user_id)
        except Users.DoesNotExist:
            return Response({'error': 'Invalid user-id'}, status=status.HTTP_404_NOT_FOUND)

        # Create product
        product = Product.create_product(
            user=user,
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
            delivery_option=delivery_option
        )

        # Log activity
        UserActivity.create_activity(user, activity="ADD_PRODUCT", discription="")

        serializer = ProductSerializer(product)
        return Response({
            'message': 'Product created successfully',
            'product_id': product.p_id,
            'product': serializer.data,
            'note': 'Upload media files using BigFileTransferHandler with this product_id',
            'upload_instructions': {
                'subject': 'PRODUCT_MEDIA',
                'product_id': product.p_id,
                'file_purpose': 'img or vid',
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
