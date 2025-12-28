from backend.permissions import HasValidTokenForUser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.models import OrderRequest, OrdProdLink, Product
from django.db.models import Q


@api_view(['GET'])
@permission_classes([HasValidTokenForUser])
def get_farmer_orders(request):
    """Get all orders for products belonging to the authenticated farmer"""
    farmer = request.user
    
    # Get all products belonging to this farmer
    farmer_products = Product.objects.filter(user_id=farmer)
    
    if not farmer_products.exists():
        return Response({'orders': []}, status=status.HTTP_200_OK)
    
    # Get all orders that contain farmer's products
    order_links = OrdProdLink.objects.filter(p_id__in=farmer_products).select_related('order_id', 'p_id')
    
    # Group orders
    orders_dict = {}
    for link in order_links:
        order = link.order_id
        if order.order_id not in orders_dict:
            orders_dict[order.order_id] = {
                'order_id': order.order_id,
                'consumer_id': order.consumer_id.user_id,
                'order_date': order.order_date,
                'total_cost': str(order.total_cost) if order.total_cost else None,
                'status': order.fullfilment_status,
                'shipping_address': order.shipping_address,
                'expected_delivery_date': order.expected_delivery_date,
                'products': []
            }
        
        orders_dict[order.order_id]['products'].append({
            'product_id': link.p_id.p_id,
            'product_name': link.p_id.name,
            'quantity': link.quantity,
            'price_at_sale': str(link.price_at_sale) if link.price_at_sale else None
        })
    
    return Response({'orders': list(orders_dict.values())}, status=status.HTTP_200_OK)
