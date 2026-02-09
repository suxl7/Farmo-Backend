from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.models import Users, Verification, Product, Connections, OrderRequest, OrdProdLink, Wallet, OrdProdLink, Transaction
from backend.permissions import HasValidTokenForUser
from rest_framework.permissions import AllowAny
from django.db.models import Q, Sum, F
from django.utils import timezone
 


@api_view(['POST'])
@permission_classes([AllowAny])
def dashboard_fullfillment(request):
    user_id = request.headers.get('user-id')
    print(user_id)
    # ✅ consistent key
    try:
        user = Users.objects.get(user_id=user_id)
    except Users.DoesNotExist:
        return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if user.is_admin:
        return Response({
            'total_farmers': get_total_farmers(),
            'active_products': get_active_products(),
            'total_consumers': get_total_consumers(),
            'verification_requests': get_verification_requests()
        }, status=status.HTTP_200_OK)

    elif user.profile_id.user_type in ['Farmer', 'VerifiedFarmer']:
        return Response({
            'username': user.get_full_name_from_userModel(),
            'connections': get_user_total_connections(user),
            'wallet_balance': get_wallet_balance(user),
            'todays_income': get_todays_income(user),
            #'total_orders': get_farmer_orderRequests(user_id)
        }, status=status.HTTP_200_OK)

    elif user.profile_id.user_type in ['Consumer', 'VerifiedConsumer']:
        return Response({
            'connections': get_user_total_connections(user_id),
            'order_requests': get_orderRequested_by_consumer(user_id),
            'username': user.get_full_name_from_userModel(),
            'connections': get_user_total_connections(user_id),
            'wallet_balance': get_wallet_balance(user_id),
        }, status=status.HTTP_200_OK)

    return Response({'detail': 'Unauthorized user type'}, status=status.HTTP_403_FORBIDDEN)


@api_view(['POST'])
@permission_classes([AllowAny])
def dashboard_fullfillment_test(request):
    user_id = request.headers.get('user-id')
    
    # ✅ consistent key
    try:
        user = Users.objects.get(user_id=user_id)
    except Users.DoesNotExist:
        return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if user.is_admin:
        return Response({
            'username': user.get_full_name_from_userModel(),
            'total_farmers': get_total_farmers(),
            'active_products': get_active_products(),
            'total_consumers': get_total_consumers(),
            'verification_requests': get_verification_requests()
        }, status=status.HTTP_200_OK)

    elif user.profile_id.user_type in ['Farmer', 'VerifiedFarmer']:
        return Response({
            'username': user.get_full_name_from_userModel(),
            'connections': get_user_total_connections(user_id),
            'wallet_balance': get_wallet_balance(user_id),
            #'todays_income': get_todays_income(user_id),
            #'total_orders': get_farmer_orderRequests(user_id)
        }, status=status.HTTP_200_OK)

    elif user.profile_id.user_type in ['Consumer', 'VerifiedConsumer']:
        return Response({
            'connections': get_user_total_connections(user_id),
            'order_requests': get_orderRequested_by_consumer(user_id)
        }, status=status.HTTP_200_OK)

    return Response({'detail': 'Unauthorized user type'}, status=status.HTTP_403_FORBIDDEN)

##########################################################################################
#                            Helper Methode Start
##########################################################################################
# def get_total_farmers():
#     return Users.objects.filter(
#         profile_id__user_type='Farmer',
#         profile_status='ACTIVATED'
#         ).count()
from django.db.models import Q

def get_total_farmers():
    return Users.objects.filter(
        Q(profile_id__user_type='Farmer', profile_status='ACTIVATED') |
        Q(profile_id__user_type='VerifiedFarmer', profile_status='ACTIVATED')
    ).count()

def get_active_products():
    return Product.objects.filter(product_status='AVAILABLE').count()

def get_total_consumers():
    return Users.objects.filter(profile_id__user_type='Consumer',
        profile_status='ACTIVATED').count()

def get_verification_requests():
    return Verification.objects.filter(status='Pending').count()

def get_user_total_connections(user_id):
    return Connections.objects.filter(
        Q(user_id=user_id) | Q(target_user_id=user_id)
        ).count()

def get_farmer_orderRequests(farmer):
    farmer_products = Product.objects.filter(user_id=farmer)
    return OrdProdLink.objects.filter(p_id__in=farmer_products, order_status = "PENDING").count()

def get_orderRequested_by_consumer(consumer):
    return OrderRequest.objects.filter(consumer_id=consumer, order_status = "PENDING").count()

def get_wallet_balance(user):
    try:
        balance = Wallet.objects.get(user_id=user).balance
    except Wallet.DoesNotExist:
        return 0
    return balance

def get_todays_income(farmer):
    # 1. Get today's date
    today = timezone.now().date()
    income_data = Transaction.objects.filter(
        transaction_to=farmer,
        transaction_date__date=today,
        status = 'SUCCESSFUL'
    ).aggregate(
        today_income = Sum(F('amount'))
    )
    # 4. Handle cases where there are no sales (returns None), default to 0
    return income_data['today_income'] or 0

def get_todays_expense(user):
    today = timezone.now().date()
    expense_data = Transaction.objects.filter(
        initiated_by=user,
        transaction_date__date=today,
        status = 'SUCCESSFUL' 
    ).aggregate(
        today_expense = Sum(F('amount'))
    )
    return expense_data['today_expense'] or 0


##########################################################################################
#                             Helper Methode End
##########################################################################################

##########################################################################################
#                            refresh_wallet Start
##########################################################################################
@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def refresh_wallet(request):
    """Get all orders for products belonging to the authenticated farmer"""
    userid = request.headers.get('user-id')
    
    if userid is None:
        return Response({'error': 'Missing user-id header'}, status=status.HTTP_400_BAD_REQUEST)
    
    balance = "20000.00"
    b = "10000.00"
    return Response(
        {
        'balance': balance,
        'todays_income': b
        },
        status=status.HTTP_200_OK)
##########################################################################################
#                            refresh_wallet End
##########################################################################################

