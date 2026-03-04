from backend.permissions import HasValidTokenForUser, IsFarmer
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.models import OrderRequest, Users, UsersProfile, Product
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
import secrets
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


##########################################################################################
#                             Order Request Start
##########################################################################################

'''
Order Request Proccessing
'''
@api_view(['POST'])
@permission_classes([AllowAny])
def order_request(request):
    """Get all orders for products belonging to the authenticated farmer"""
    consumer = request.headers.get('user-id')

    data = request.data

    expected_delivery_within = data.get('expected_delivery_within') 
    shipping_address = data.get('shipping_address')
    total_cost = data.get('total_cost')
    product_id = data.get('product_id')
    quantity = data.get('quantity', 0.0)
    message = data.get('message')
    payment_method = data.get('payment')
    

    expected_delivery_date = timezone.now() + timedelta(days=expected_delivery_within)
    try:
        product = Product.objects.get(p_id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found!'}, status=status.HTTP_404_NOT_FOUND)
    
    cost_per_unit = product.cost_per_unit

    messageJSON = [{
        "date-time": str(timezone.now()),
        "by" : consumer,
        "message": message
        }]
    print(payment_method)
    if str(payment_method).lower() in ['cashondelivery', 'cod', 'cash on delivery', 'cash', 'on delivery', 'Cash On Delivery']:
        payment_method = 'CashOnDelivery'
    else:
        payment_method = 'WALLET'

    print(payment_method)
    consumer = Users.objects.get(user_id=consumer)
    total_cost = Decimal(str(quantity)) * cost_per_unit
    order_id = f"ORD-{product.user_id.user_id}-id-{secrets.token_hex(3).upper()}"
    try:
        order = OrderRequest.create_order(
            order_id=order_id,
            consumer_id=consumer,
            product = product,
            quantity=quantity,
            total_cost=total_cost,
            shipping_address=shipping_address,
            expected_delivery_date=expected_delivery_date,
            message=messageJSON,
            payment_method=payment_method
        )
    
        
        return Response({'order_id': order.order_id, 'otp': order.ORDER_OTP}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

##########################################################################################
#                             Order Request End
##########################################################################################
##########################################################################################
#                             all_incomming_orders_for_farmer Start
##########################################################################################

    
'''
This is for the farmer he gets his incomming orders list.
'''
@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def all_incomming_orders_for_farmer(request):

    # user = request.headers.get('user_id')

    # data = request.data

    # order_status = data.get('order_status')

    # user_type = Users.objects.get(user_id=user).profile_id.user_type

    # if user_type.lower() in ['consumer' , 'verifiedconsumer']:
    #     return Response({'error': 'You are not a farmer.This is for only farmers'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # if user_type.lower() in ['farmer', 'verifiedfarmer']:
    #     try:
    #         # product IDs for this farmer
    #         products = Product.objects.filter(user_id=user).values_list('p_id', flat=True)

    #         # distinct order IDs linked to those products
           
            
    #         if order_status.lower() == 'all':  
    #             # consumer IDs for those orders
    #             consumers = OrderRequest.objects.filter(product__in=products).values_list('consumer_id', flat=True)
    #         else:
    #             # consumers = OrderRequest.objects.filter(order_id__in=orders, order_status=order_status).values_list('consumer_id', flat=True)

    #         # consumer names via UsersProfile
    #         profiles = UsersProfile.objects.filter(
    #             pk__in=Users.objects.filter(user_id__in=consumers).values_list("profile_id", flat=True)
    #         )
    #         consumer_names = [profile.get_Full_Name for profile in profiles]

    #         # total costs and ordered dates
    #         total_costs = list(OrderRequest.objects.filter(order_id__in=orders).values_list('total_cost', flat=True))
    #         ordered_dates = list(OrderRequest.objects.filter(order_id__in=orders).values_list('ordered_date', flat=True))

    #         return Response({
    #             'orders': list(orders),
    #             'consumers': list(consumers),
    #             'consumer_names': consumer_names,
    #             'total_costs': total_costs,
    #             'ordered_dates': ordered_dates
    #             }, status=status.HTTP_200_OK)

    #     except ObjectDoesNotExist:
    #         return Response({'error': 'No orders found!'}, status=status.HTTP_404_NOT_FOUND)
        
    return Response({'error': 'Bad Request!'}, status=status.HTTP_400_BAD_REQUEST)
   
##########################################################################################
#                             all_incomming_orders_for_farmer End
##########################################################################################

##########################################################################################
#                             all_consumer_orders Start
##########################################################################################

'''
This is for the consumer he gets his ordered products list.
'''
@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def all_consumer_orders(request):

    user = request.headers.get('user_id')
    data = request.data
    order_status = data.get('order_status')

    try:
        orders = OrderRequest.objects.filter(consumer_id=user, order_status=order_status).values_list('order_id', flat=True)
        ordered_date = OrderRequest.objects.filter(order_id__in=orders).values_list('ordered_date', flat=True)
        price = OrderRequest.objects.filter(order_id__in=orders).values_list('total_cost', flat=True)
        #products_id = OrdProdLink.objects.filter(order_id__in=orders).values_list('p_id', flat=True)
        p_id = []
        # product_name = []
        # for i in range(len(orders)):
        #     p_id[i] = OrdProdLink.objects.filter(order_id=orders[i]).values_list('p_id', flat=True)
        #     if len(p_id[i]) == 1:
        #         product_name[i] = Product.objects.filter(p_id=p_id[i][0]).values_list('name', flat=True)
        
        #     elif len(p_id[i]) >= 2:
        #         product_name[i] = Product.objects.filter(p_id=p_id[i][0]).values_list('name', flat=True)
        #         product_name[i] = product_name[i].append(Product.objects.filter(p_id=p_id[i][1]).values_list('name', flat=True))
        #         if len(p_id[i]) > 2:
        #            product_name[i] = product_name[i].append("and other items.")

        # return Response({
        #         'orders': list(orders),
        #         'ordered_date': list(ordered_date),
        #         'price': list(price),
        #         'product_name': list(product_name)
        #         }, status=status.HTTP_200_OK)  
           
    except ObjectDoesNotExist:
        return Response({'error': 'No orders found!'}, status=status.HTTP_404_NOT_FOUND)
##########################################################################################
#                              all Consumer End
##########################################################################################
'''get order detail'''

@api_view(['POST'])
@permission_classes([AllowAny])
def get_order_detail(request):
    """Get all orders for products belonging to the authenticated farmer"""
    user = request.headers.get('user-id')
    data = request.data
    order_id = data.get('order_id')

    try:
        from backend.serializers import OrderRequestSerializer
        order = OrderRequest.objects.get(order_id=order_id)
        if order.consumer_id.user_id != user:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        data = OrderRequestSerializer(order).data
        cost_per_unit = order.product.cost_per_unit
        data.pop('order_otp', None)
        data["cost_per_unit"] = cost_per_unit
        return Response(data, status=status.HTTP_200_OK)

    except ObjectDoesNotExist:
        return Response({'error': 'No orders found!'}, status=status.HTTP_404_NOT_FOUND)
    
##########################################################################################
#                             get_order_detail End
##########################################################################################
##########################################################################################
#                             Confirm Delivery Start
##########################################################################################

@api_view(['POST'])
@permission_classes([AllowAny, IsFarmer])
def order_status_update(request):
    userid = request.headers.get('user-id')
    order_id = request.data.get('order_id')
    otp = request.data.get('otp')
    order_status = request.data.get('status')

    try:
        order = OrderRequest.objects.get(order_id=order_id, ORDER_OTP=otp)
        
        if order.product.user_id.user_id != userid:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        if order_status.lower() in ['accepted', 'accept']:
            order.order_status = 'ACCEPTED'
        elif order_status.lower() in ['rejected', 'reject']:
            order.order_status = 'REJECTED'
        else:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        order.save()
        return Response({'message': 'Order status updated successfully'}, status=status.HTTP_200_OK)
    except ObjectDoesNotExist:
        return Response({'error': 'Invalid order ID'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        if order.order_status == 'REJECTED':
            order.order_status = 'ACCEPTED'
            order.save()
            return Response({'message': 'Order status updated successfully'}, status=status.HTTP_200_OK)
        
        return Response({'error': 'Already Accepted.'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_delivery(request):
    otp = request.data.get('otp')
    order_id = request.data.get('order_id')
    paid_amount_by_wallet = request.data.get('paid_amount_by_wallet')


    from backend.service_frontend.transaction import transfer_fund
    
    try:
        order = OrderRequest.objects.get(order_id=order_id, ORDER_OTP=otp)

        if order.order_status == 'DELIVERED':
            return Response({'error': 'Order already delivered.'}, status=status.HTTP_400_BAD_REQUEST)
        elif order.order_status != 'ACCEPTED':
            return Response({'error': 'Order is not yet accepted.'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment_method = order.payment_method
        if payment_method == 'WALLET':
            transfer_fund(order, paid_amount_by_wallet)
        order.order_status = 'DELIVERED'
        order.save()
        return Response({'message': 'Order delivered successfully'}, status=status.HTTP_200_OK)
    except ObjectDoesNotExist:
        return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
##########################################################################################
#                            Confirm Delivery End
##########################################################################################
 