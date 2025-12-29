from backend.permissions import HasValidTokenForUser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.models import OrderRequest, OrdProdLink, Product
from django.db.models import Q


@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def orderRequests(request):
    """Get all orders for products belonging to the authenticated farmer"""
    
    return Response({'orders': list(orders_dict.values())}, status=status.HTTP_200_OK)
