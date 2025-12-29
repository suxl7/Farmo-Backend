from backend.permissions import HasValidTokenForUser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.models import OrderRequest, OrdProdLink, Users, UsersProfile, Product
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
import secrets



'''
Order Request Proccessing
'''
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

    
'''
This is for the farmer he gets his incomming orders list.
'''
@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def all_incomming_orders_for_farmer(request):

    user = request.headers.get('userid')

    data = request.data

    user_type = Users.objects.get(user_id=user).profile_id.user_type

    if user_type.lower() in ['consumer' , 'verifiedconsumer']:
        return Response({'error': 'You are not a farmer.This is for only farmers'}, status=status.HTTP_401_UNAUTHORIZED)
    
    if user_type.lower() in ['farmer', 'verifiedfarmer']:
        try:
            # product IDs for this farmer
            products = Product.objects.filter(user_id=user).values_list('p_id', flat=True)
            '''
            flat=true means with example?
            
            '''
            # distinct order IDs linked to those products
            orders = OrdProdLink.objects.filter(p_id__in=products).values_list('order_id', flat=True).distinct()

            # consumer IDs for those orders
            consumers = OrderRequest.objects.filter(order_id__in=orders).values_list('consumer_id', flat=True)

            # consumer names via UsersProfile
            profiles = UsersProfile.objects.filter(
                pk__in=Users.objects.filter(user_id__in=consumers).values_list("profile_id", flat=True)
            )
            consumer_names = [profile.get_Full_Name for profile in profiles]

            # total costs and ordered dates
            total_costs = list(OrderRequest.objects.filter(order_id__in=orders).values_list('total_cost', flat=True))
            ordered_dates = list(OrderRequest.objects.filter(order_id__in=orders).values_list('ordered_date', flat=True))

            return Response({
                'orders': list(orders),
                'consumers': list(consumers),
                'consumer_names': consumer_names,
                'total_costs': total_costs,
                'ordered_dates': ordered_dates
                }, status=status.HTTP_200_OK)

        except ObjectDoesNotExist:
            return Response({'error': 'No orders found!'}, status=status.HTTP_404_NOT_FOUND)
        
    return Response({'error': 'Bad Request!'}, status=status.HTTP_400_BAD_REQUEST)
   


'''
This is for the consumer he gets his orders list.
'''
@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def all_consumer_orders(request):



    return Response({'error': 'Bad Request!'}, status=status.HTTP_400_BAD_REQUEST)