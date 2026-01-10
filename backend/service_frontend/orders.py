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
    total_cost = data.get('total_cost')
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

    user = request.headers.get('user_id')

    data = request.data

    order_status = data.get('order_status')

    user_type = Users.objects.get(user_id=user).profile_id.user_type

    if user_type.lower() in ['consumer' , 'verifiedconsumer']:
        return Response({'error': 'You are not a farmer.This is for only farmers'}, status=status.HTTP_401_UNAUTHORIZED)
    
    if user_type.lower() in ['farmer', 'verifiedfarmer']:
        try:
            # product IDs for this farmer
            products = Product.objects.filter(user_id=user).values_list('p_id', flat=True)

            # distinct order IDs linked to those products
            orders = OrdProdLink.objects.filter(p_id__in=products).values_list('order_id', flat=True).distinct()
            
            if order_status.lower() == 'all':  
                # consumer IDs for those orders
                consumers = OrderRequest.objects.filter(order_id__in=orders).values_list('consumer_id', flat=True)
            else:
                consumers = OrderRequest.objects.filter(order_id__in=orders, order_status=order_status).values_list('consumer_id', flat=True)

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
        product_name = []
        for i in range(len(orders)):
            p_id[i] = OrdProdLink.objects.filter(order_id=orders[i]).values_list('p_id', flat=True)
            if len(p_id[i]) == 1:
                product_name[i] = Product.objects.filter(p_id=p_id[i][0]).values_list('name', flat=True)
        
            elif len(p_id[i]) >= 2:
                product_name[i] = Product.objects.filter(p_id=p_id[i][0]).values_list('name', flat=True)
                product_name[i] = product_name[i].append(Product.objects.filter(p_id=p_id[i][1]).values_list('name', flat=True))
                if len(p_id[i]) > 2:
                   product_name[i] = product_name[i].append("and other items.")

        return Response({
                'orders': list(orders),
                'ordered_date': list(ordered_date),
                'price': list(price),
                'product_name': list(product_name)
                }, status=status.HTTP_200_OK)  
           
    except ObjectDoesNotExist:
        return Response({'error': 'No orders found!'}, status=status.HTTP_404_NOT_FOUND)
    

'''get order detail'''
@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def get_order_detail(request):
    """Get all orders for products belonging to the authenticated farmer"""
    user = request.headers.get('user_id')
    data = request.data
    order_id = data.get('order_id')

    try:
        order = OrderRequest.objects.get(order_id=order_id)
        ordered_date = order.ordered_date
        price = order.total_cost
        products_id = OrdProdLink.objects.filter(order_id=order_id).values_list('p_id', flat=True)
        product_quantity = OrdProdLink.objects.filter(order_id=order_id).values_list('quantity', flat=True)
        product_cost_per_unit = OrdProdLink.objects.filter(order_id=order_id).values_list('cost_per_unit', flat=True)
        product_name = []
        for i in range(len(products_id)):
            product_name[i] = Product.objects.filter(p_id=products_id[i]).values_list('name', flat=True)
        
        order_status = order.order_status
        order_shipping_adderss = order.shipping_address
        order_expected_delivery_date = order.expected_delivery_date
        order_otp = order.ORDER_OTP

        consumer_id = order.consumer_id
        farmer_id = Product.objects.get(p_id=products_id[0]).values_list('user_id', flat=True) 

        return Response({
                'order_id': order_id,
                'farmer_id': farmer_id,
                'consumer_id': consumer_id,
                'ordered_date': ordered_date,
                'product_id': list(products_id),
                'product_name': list(product_name),
                'product_quantity': list(product_quantity),
                'product_cost_per_unit': list(product_cost_per_unit),
                'price': price,
                'order_status': order_status,
                'order_shipping_adderss': order_shipping_adderss,
                'order_expected_delivery_date': order_expected_delivery_date,
                'order_otp': order_otp
                }, status=status.HTTP_200_OK)

    except ObjectDoesNotExist:
        return Response({'error': 'No orders found!'}, status=status.HTTP_404_NOT_FOUND)
    
    