'''
This file is for updating farm product from json to database
'''
import json
from backend.models import FarmProducts
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.permissions import HasValidTokenForUser, IsFarmer, IsAdmin
from rest_framework.permissions import AllowAny


@api_view(['POST'])
@permission_classes([AllowAny]) # Adjust permissions as needed
def update_farm_products(request):
    # Ensure data is a list
    data_list = request.data if isinstance(request.data, list) else [request.data]
    
    if "farm_products" in request.data:
        data_list = request.data["farm_products"]

    new_products = []
    for item in data_list:
        # Create an instance with the new category field
        new_products.append(FarmProducts(
            id=item.get('id'),
            primary_name=item.get('english_name') or item.get('primary_name'),
            secondary_name=item.get('nepali_name') or item.get('secondary_name'),
            category=item.get('category') # Successfully captures the category slug
        ))

    try:
        # bulk_create is highly efficient for large datasets
        # update_conflicts=True (Django 4.1+) updates existing records instead of skipping them
        FarmProducts.objects.bulk_create(
            new_products,
            update_conflicts=True,
            unique_fields=['id'],
            update_fields=['primary_name', 'secondary_name', 'category']
        )
        return Response({'message': f'Successfully updated {len(new_products)} products'}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
@permission_classes([AllowAny])
def download_farm_products(request):
    products = FarmProducts.objects.all().order_by('id')
    
    data = []
    for p in products:
        data.append({
            "id": p.id,
            "english_name": p.primary_name,
            "nepali_name": p.secondary_name,
            "category": p.category, # Returns the slug (e.g., 'vegetable')
            "category_display": p.get_category_display() # Optional: Returns 'Vegetable'
        })
    
    return Response({"farm_products": data})