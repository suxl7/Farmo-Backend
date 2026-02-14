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
@permission_classes([AllowAny])
def update_farm_products(request):
    # Ensure data is a list
    data_list = request.data if isinstance(request.data, list) else [request.data]
    
    new_products = []
    for item in data_list:
        # Create an instance but don't save to DB yet
        new_products.append(FarmProducts(
            id=item.get('id'),
            primary_name=item.get('primary_name'),
            secondary_name=item.get('secondary_name')
        ))

    try:
        # Use bulk_create to save everything in ONE database query
        # ignore_conflicts=True prevents crashing if an ID already exists
        FarmProducts.objects.bulk_create(new_products)
        return Response({'message': f'Successfully uploaded {len(new_products)} products'}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET'])
@permission_classes([AllowAny])
def download_farm_products(request):
    products = FarmProducts.objects.all().order_by('id')
    
    # Manually formatting if you don't want to use a Serializer
    data = []
    for p in products:
        data.append({
            "id": p.id,
            "english_name": p.primary_name,
            "nepali_name": p.secondary_name
        })
    
    return Response({"farm_products": data})