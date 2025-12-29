from backend.permissions import HasValidTokenForUser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.models import OrderRequest, OrdProdLink, Product, UsersProfile
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
import secrets




@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def order_request(request):
    """Get all orders for products belonging to the authenticated farmer"""
    consumer = request.headers.get('userid')

    data = request.data

    expected_delivery_date = data.get('expected_delivery_date') 
    shipping_address = data.get('shipping_address')
    ordered_date = data.get('ordered_date')
    total_cost = data.get('total_cost')
    order_status = 'PENDING'
    product_id = data.get('product_id', [])
    quantity = data.get('quantity', [])
    cost_per_unit = data.get('cost_per_unit', [])

    total_cost_afterCalc = 0
    for i in range(len(quantity)):
         total_cost_afterCalc = total_cost_afterCalc + (quantity[i] * cost_per_unit[i])
    
    if total_cost_afterCalc != total_cost:
        return Response({'error': 'Total cost mismatch!'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        order_id = OrderRequest.create_order(
            consumer_id=consumer,
            total_cost=total_cost_afterCalc,
            shipping_address=shipping_address,
            expected_delivery_date=expected_delivery_date
        )
        for i in range(len(product_id)):
            flag = OrdProdLink.objects.create(
                order_id=order_id,
                p_id=product_id[i],
                quantity=quantity[i],
                cost_per_unit=cost_per_unit[i]
            )
            if not flag:
                raise Exception('Error in creating order!')
        
        return Response({'order_id': order_id, 'order_places': 'successfull!'}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': e}, status=status.HTTP_404_NOT_FOUND)

    
@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def see_all_orders(request):
    user = request.headers.get('userid')

    data = request.data

    #user_type = Users.objects.get(user_id=user, profile_
