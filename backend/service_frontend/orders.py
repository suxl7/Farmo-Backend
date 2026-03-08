from backend.permissions import HasValidTokenForUser, IsFarmer, IsFarmerOrConsumer
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
    message = data.get('message', 'Please deliver quickly.')
    payment_method = data.get('payment', 'Wallet')
    
    if not all([expected_delivery_within, shipping_address, total_cost, product_id, payment_method, quantity]):
        return Response({'error': 'Required fields are missing.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        product = Product.objects.get(p_id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found!'}, status=status.HTTP_404_NOT_FOUND)
    
    # Calculate cost with discount
    cost_per_unit = Decimal(str(product.cost_per_unit))
    quantity_decimal = Decimal(str(quantity))
    
    if product.discount and product.discount_type:
        discount_value = Decimal(str(product.discount))
        if product.discount_type.lower() == 'percentage':
            cost_per_unit = cost_per_unit - (cost_per_unit * discount_value / 100)
        elif product.discount_type.lower() in ['fixed', 'flat']:
            cost_per_unit = cost_per_unit - discount_value
    
    calculated_cost = cost_per_unit * quantity_decimal
    
    # Validate total cost (allow 0.01 difference for rounding)
    if abs(calculated_cost - Decimal(str(total_cost))) > Decimal('0.01'):
        return Response({
            'error': 'Cost mismatch!',
            'expected': str(calculated_cost),
            'received': str(total_cost)
        }, status=status.HTTP_400_BAD_REQUEST)

    expected_delivery_date = timezone.now() + timedelta(days=expected_delivery_within)

    messageJSON = [{
        "date-time": str(timezone.now()),
        "by": "consumer",
        "user_id": consumer,
        "message": message
    }]
    
    if str(payment_method).lower() in ['cashondelivery', 'cod', 'cash on delivery', 'cash', 'on delivery']:
        payment_method = 'CashOnDelivery'
    else:
        payment_method = 'WALLET'

    consumer_obj = Users.objects.get(user_id=consumer)
    order_id = f"ORD-{product.user_id.user_id}-id-{secrets.token_hex(3).upper()}"
    
    try:
        order = OrderRequest.create_order(
            order_id=order_id,
            consumer_id=consumer_obj,
            product=product,
            quantity=quantity_decimal,
            total_cost=calculated_cost,
            shipping_address=shipping_address,
            expected_delivery_date=expected_delivery_date,
            message=messageJSON,
            payment_method=payment_method
        )
        from backend.utils.score_tracker import track_product_view
        user = Users.objects.get(user_id=consumer)
        track_product_view(user, product, 1)
        return Response({
            'order_id': order.order_id,
            'otp': str(order.ORDER_OTP),
            'ordered_date': order.ordered_date.strftime("%Y-%m-%d %H:%M:%S"),
            'total_cost': str(order.total_cost)
        }, status=status.HTTP_200_OK)

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
        from backend.models import Transaction
        
        order = OrderRequest.objects.get(order_id=order_id)
        user_obj = Users.objects.get(user_id=user)
        
        # Check authorization: admin, product owner, or order requester
        if not (user_obj.is_admin or 
                order.consumer_id.user_id == user or 
                order.product.user_id.user_id == user):
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        
        data = OrderRequestSerializer(order).data
        cost_per_unit = order.product.cost_per_unit
        quantity_unit = order.product.product_unit
        data["quantity_unit"] = quantity_unit
        data["cost_per_unit"] = cost_per_unit
        
        # Get transaction status
        try:
            transaction = Transaction.objects.get(order=order)
            data['transaction_status'] = transaction.status
        except Transaction.DoesNotExist:
            data['transaction_status'] = 'not_initiated'
        
        # Format dates
        if order.ordered_date:
            data['ordered_date'] = order.ordered_date.strftime('%d-%m-%Y %H:%M %Z')
        if order.latest_update:
            data['latest_update'] = order.latest_update.strftime('%d-%m-%Y %H:%M %Z')
        if order.expected_delivery_date:
            data['expected_delivery_date'] = order.expected_delivery_date.strftime('%d-%m-%Y')
        
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
@permission_classes([AllowAny, IsFarmerOrConsumer])
def order_status_update(request):
    userid = request.headers.get('user-id')
    order_id = request.data.get('order_id')
    otp = request.data.get('otp')
    order_status = request.data.get('status')
    message = request.data.get('message')

    try:
        order = OrderRequest.objects.get(order_id=order_id, ORDER_OTP=otp)
        current_status = order.order_status
        new_status = str(order_status).lower()
        
        # Status transition validation
        if current_status == 'ACCEPTED':
            return Response({'error': 'Cannot change status of accepted order'}, status=status.HTTP_400_BAD_REQUEST)
        
        if current_status == 'PENDING':
            if new_status not in ['accepted', 'accept', 'rejected', 'reject']:
                return Response({'error': 'Pending orders can only be accepted or rejected'}, status=status.HTTP_400_BAD_REQUEST)
        
        if current_status == 'REJECTED':
            if new_status not in ['pending', 'resent']:
                return Response({'error': 'Rejected orders can only be set to pending'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check authorization based on status
        if new_status in ['accepted', 'accept', 'rejected', 'reject']:
            # Only product owner (farmer) can accept/reject
            if order.product.user_id.user_id != userid:
                return Response({'error': 'Only product owner can accept/reject orders'}, status=status.HTTP_401_UNAUTHORIZED)
        elif new_status in ['pending', 'resent']:
            # Only order requester (consumer) can set to pending
            if order.consumer_id.user_id != userid:
                return Response({'error': 'Only buyer can set order to pending'}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update status
        if new_status in ['accepted', 'accept']:
            order.order_status = 'ACCEPTED'
        elif new_status in ['rejected', 'reject']:
            order.order_status = 'REJECTED'
        elif new_status in ['pending', 'resent']:
            order.order_status = 'PENDING'
        
        # Append message
        if message:
            messages = order.message or []
            by_type = "farmer" if order.product.user_id.user_id == userid else "consumer"
            messages.append({
                "date-time": str(timezone.now()),
                "by": by_type,
                "user_id": userid,
                "message": message
            })
            order.message = messages
        
        if order.order_status == 'ACCEPTED':
            _check_and_update_product_quantity(order)

        order.save()

        return Response({'message': 'Order status updated successfully'}, status=status.HTTP_200_OK)
    
    except ObjectDoesNotExist:
        return Response({'error': 'Invalid order ID'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # print(e)
        if order.order_status == 'REJECTED':
            order.order_status = 'ACCEPTED'
            _check_and_update_product_quantity(order)
            order.save()
            return Response({'message': 'Order status updated successfully'}, status=status.HTTP_200_OK)
        
        return Response({'error': 'Less Product Quantity or Already Accepted.'}, status=status.HTTP_400_BAD_REQUEST)

def _check_and_update_product_quantity(order):
    product = order.product
    quantity = Decimal(str(order.ordered_quantity))
    product_quantity = Decimal(str(product.quantity_available))
    if quantity > product_quantity:
        raise ValueError("Insufficient quantity available")
    product.quantity_available -= quantity
    product.save()
    return 


@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_delivery(request):
    userid = request.headers.get('user-id')

    otp = request.data.get('otp')
    order_id = request.data.get('order_id')
    # payment_method = request.data.get('payment_method') # ['WALLET', 'Cash', 'BOTH']
    #paid_amount_by_wallet = request.data.get('paid_amount_by_wallet')


    from backend.service_frontend.transaction import transfer_fund
    
    try:
        order = OrderRequest.objects.get(order_id=order_id, ORDER_OTP=otp)
    
        if order.product.user_id.user_id != userid or order.consumer_id.user_id != userid or not Users.objects.get(user_id=userid).is_admin:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if order.order_status == 'DELIVERED':
            return Response({'error': 'Order already delivered.'}, status=status.HTTP_400_BAD_REQUEST)
        elif order.order_status in ['PENDING', 'REJECTED']:
            return Response({'error': 'Order is not yet accepted.'}, status=status.HTTP_400_BAD_REQUEST)
        
        paid_amount_by_wallet = Decimal(order.total_cost)
        payment_method = str(order.payment_method)
        message = "Delivered."
        if order.order_status == 'PENDING_DELIVERY':
            order.order_status = 'DELIVERED'
            message = "Order is delivered."
        elif payment_method == 'WALLET':
            transfer_fund(order, paid_amount_by_wallet)
            order.order_status = 'DELIVERED'
            message = "Order is delivered."
        else:
            order.order_status = 'PENDING_DELIVERY'
            message = "Order is delivered but payment is pending. Need to confirm delivery from farmer."
        

        order.save()
        
        return Response({'message': message}, status=status.HTTP_200_OK)
    except ObjectDoesNotExist:
        return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
##########################################################################################
#                            Confirm Delivery End
##########################################################################################
 


##########################################################################################
#                            Get Orders List Start
##########################################################################################
from backend.permissions import IsFarmerOrConsumer

@api_view(['POST'])
@permission_classes([AllowAny, IsFarmerOrConsumer])
def get_orders_list(request):
    from django.core.paginator import Paginator
    from datetime import datetime
    
    user_id = request.headers.get('user-id')
    order_type = request.data.get('type', 'all').lower()  # 'all', 'sent', 'received'
    order_status = request.data.get('status', 'all').lower()  # 'all', 'pending', 'accepted', 'rejected', 'delivered'
    date_from = request.data.get('date_from')  # yyyy-mm-dd
    date_to = request.data.get('date_to')  # yyyy-mm-dd
    page = request.data.get('page', 1)
    
    try:
        user = Users.objects.select_related('profile_id').get(user_id=user_id)
        user_type = user.profile_id.user_type.lower()
        
        if user_type not in ['farmer', 'verifiedfarmer', 'consumer', 'verifiedconsumer']:
            return Response({'error': 'Unauthorized user type'}, status=status.HTTP_403_FORBIDDEN)
        
        query = Q()
        
        # Filter by order type
        order_type_normalized = str(order_type).replace(' ', '').lower()
        if 'requested' in order_type_normalized:
            query &= Q(consumer_id=user)
        elif 'received' in order_type_normalized:
            query &= Q(product__user_id=user)
        else:  # 'all'
            query &= Q(consumer_id=user) | Q(product__user_id=user)
        
        # Filter by order status
        if order_status != 'all':
            status_map = {
                'pending': 'PENDING',
                'accepted': 'ACCEPTED',
                'rejected': 'REJECTED',
                'delivered': ['DELIVERED', 'PENDING_DELIVERY'],
                'cancelled': 'CANCELLED'
            }
            mapped_status = status_map.get(order_status, 'PENDING')
            if isinstance(mapped_status, list):
                query &= Q(order_status__in=mapped_status)
            else:
                query &= Q(order_status=mapped_status)
        
        # Filter by date range
        if date_from:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query &= Q(ordered_date__gte=date_from_obj)
        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            query &= Q(ordered_date__lte=date_to_obj)
        
        orders = OrderRequest.objects.filter(query).select_related(
            'consumer_id__profile_id', 'product__user_id__profile_id', 'product'
        ).order_by('-latest_update')
        
        paginator = Paginator(orders, 15)
        page_obj = paginator.get_page(page)
        
        data = []
        for order in page_obj:
            is_sent = order.consumer_id.user_id == user_id
            foreign_user = order.product.user_id if is_sent else order.consumer_id
            
            # Check if user can cancel
            can_cancel = (
                is_sent and 
                order.order_status not in ['DELIVERED', 'CANCELLED']
            )
            
            data.append({
                'order_id': order.order_id,
                'product_id': order.product.p_id,
                'product_name': order.product.name,
                'cost': str(order.total_cost),
                'order_date': order.ordered_date.strftime('%Y-%m-%d::%H:%M'),
                'latest_update': order.latest_update.strftime('%Y-%m-%d') if order.latest_update else None,
                'foreign_user_id': foreign_user.user_id,
                'foreign_user_name': foreign_user.get_full_name_from_userModel(),
                'type': 'sent' if is_sent else 'received',
                'status': order.order_status.lower(),
                'can_cancel': can_cancel
            })
        
        return Response({
            'orders': data,
            'total': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }, status=status.HTTP_200_OK)
        
    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

##########################################################################################
#                            Get Orders List End
##########################################################################################


##########################################################################################
#                            Cancel Order Start
##########################################################################################

@api_view(['POST'])
@permission_classes([AllowAny])
def cancel_order(request):
    user_id = request.headers.get('user-id')
    order_id = request.data.get('order_id')
    otp = request.data.get('otp')
    
    try:
        order = OrderRequest.objects.get(order_id=order_id, ORDER_OTP=otp)
        
        if order.consumer_id.user_id != user_id:
            return Response({'error': 'Only buyer can cancel order'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if order.order_status == 'DELIVERED':
            return Response({'error': 'Cannot cancel delivered order'}, status=status.HTTP_400_BAD_REQUEST)
        
        if order.order_status == 'ACCEPTED':
            product = order.product
            product.quantity_available += Decimal(str(order.ordered_quantity))
            product.save()
        
        order.order_status = 'CANCELLED'
        order.latest_update = timezone.now()
        order.save()
        
        return Response({'message': 'Order cancelled successfully'}, status=status.HTTP_200_OK)
        
    except OrderRequest.DoesNotExist:
        return Response({'error': 'Order not found or invalid OTP'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

##########################################################################################
#                            Cancel Order End
##########################################################################################
