from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.models import Users, Verification, Product, Connections, OrderRequest, OrdProdLink, Wallet, OrdProdLink
from backend.permissions import HasValidTokenForUser
from django.db.models import Q, Sum, F
from django.utils import timezone
 


@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def dashboard_fullfillment(request):
    if request.userid.is_admin:
        return Response({
        'total_farmers': get_total_farmers(),
        'active_products': get_active_products(),
        'total_consumers': get_total_consumers(),
        'verification_requests': get_verification_requests()
        }, status=status.HTTP_200_OK)
    
    elif request.userid.profile_id.user_type == 'Farmer':
        return Response({
        'total_orders': get_farmer_orderRequests(request.userid)
        }, status=status.HTTP_200_OK)


def get_total_farmers():
    return Users.objects.filter(
        profile_id__user_type='Farmer',
        profile_status='ACTIVATED'
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

def get_wallet_balance(user_id):
    return Wallet.objects.get(user_id=user_id).amount

def get_todays_income(farmer):
    # 1. Get today's date
    today = timezone.now().date()
    
    # 2. Query OrdProdLink to sum up the specific items sold by this farmer
    income_data = OrdProdLink.objects.filter(
        # Filter 1: Ensure the product belongs to the specific farmer
        p_id__user_id=farmer,
        
        # Filter 2: Look for transactions that happened today
        # We traverse: OrdProdLink -> OrderRequest -> Transaction
        order_id__transaction__transaction_date__date=today,
        
        # Filter 3: Ensure the transaction was successful
        # (Replace 'SUCCESS' with whatever string you use for completed payments, e.g., 'COMPLETED')
        order_id__transaction__status='SUCCESS' 
    ).aggregate(
        # 3. Calculate total: Quantity * Price at Sale
        today_income=Sum(F('quantity') * F('price_at_sale'))
    )

    # 4. Handle cases where there are no sales (returns None), default to 0
    return income_data['total_income'] or 0

