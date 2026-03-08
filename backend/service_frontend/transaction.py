from backend.models import Users, OrderRequest, Wallet, Transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.permissions import HasValidTokenForUser, IsAdmin, IsFarmerOrConsumer, IsFarmer, IsConsumer
from django.db.models import *
from django.utils import timezone

##########################################################################################
#                            Transfer fund Start
##########################################################################################

def transfer_fund(order, paid_amount_by_wallet):
    try:
        
        transaction = Transaction.objects.get(order=order)
        if transaction.status == 'SUCCESSFUL':
            return

        _transfer_fund_to_wallet(order.consumer_id, order.product.user_id, paid_amount_by_wallet)
        
        transaction.amount = order.total_cost
        transaction.status = 'SUCCESSFUL'
        history = transaction.status_history
        history.append({'status': 'SUCCESSFUL', 'date': str(timezone.now())})
        transaction.status_history = history
        transaction.updated_at = timezone.now()
        transaction.save()

    except OrderRequest.DoesNotExist:
        raise Exception('Order not found')
    except Transaction.DoesNotExist:
        raise Exception('Transaction not found')
    except Exception as e:
        raise Exception(str(e))
  

def _transfer_fund_to_wallet(sender, receiver, amount):
    try:
        sender_wallet = Wallet.objects.get(user_id=sender)
        receiver_wallet = Wallet.objects.get(user_id=receiver)
        if not (sender_wallet.is_active and receiver_wallet.is_active):
            raise Exception('Farmer\'s and Consumer\'s, both Wallet is not activited')
        if sender_wallet.is_active == False:
            raise Exception('Consumer\'s Wallet is not activited')
        if receiver_wallet.is_active == False:
            raise Exception('Farmer\'s Wallet is not activited')
       
        if sender_wallet.balance < amount:
            raise Exception('Insufficient balance')

        
        sender_wallet.balance -= amount
        receiver_wallet.balance += amount
        print(amount)
        print(sender_wallet.balance)
        print(receiver_wallet.balance)
        sender_wallet.save()
        receiver_wallet.save()

    except Wallet.DoesNotExist:
        raise Exception('Wallet not found')
    except Exception as e:
        raise Exception(str(e))




##########################################################################################
#                            Transfer fund End
##########################################################################################

##########################################################################################
#                            Transfer history Start
##########################################################################################
from rest_framework.permissions import AllowAny

@api_view(['POST'])
@permission_classes([AllowAny, IsFarmerOrConsumer])
def recent_transactions(request):
    """Get recent transactions for the authenticated user (last 3 days, max 8)"""
    user_id = request.headers.get('user-id')
    
    try:
        user = Users.objects.get(user_id=user_id)
        three_days_ago = timezone.now() - timezone.timedelta(days=3)
        
        # Get transactions where user is sender or receiver
        transactions = Transaction.objects.filter(
            Q(initiated_by=user) | Q(transaction_to=user),
            transaction_date__gte=three_days_ago
        ).select_related('initiated_by__profile_id', 'transaction_to__profile_id').order_by('-transaction_date')[:8]
        
        data = []
        for txn in transactions:
            # Determine if credit or debit
            is_credit = txn.transaction_to.user_id == user_id
            other_user = txn.initiated_by if is_credit else txn.transaction_to
            
            data.append({
                'transaction_id': txn.transaction_id,
                'amount': str(txn.amount),
                'type': 'CR' if is_credit else 'DR',
                'other_party_id': other_user.user_id,
                'other_party_name': other_user.get_full_name_from_userModel(),
                'date': txn.transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': txn.status
            })
        
        
        return Response({'transaction':data}, status=status.HTTP_200_OK)
        
    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

##########################################################################################
#                            Transfer history End
##########################################################################################

##########################################################################################
#                            Transaction History Grouped by Date Start
##########################################################################################
from collections import defaultdict
from decimal import Decimal

from datetime import datetime

@api_view(['POST'])
@permission_classes([AllowAny, IsFarmerOrConsumer])
def transaction_history(request):
    """Get transaction history grouped by date with closing balance and filters"""
    user_id = request.headers.get('user-id')
    txn_type = request.data.get('type', 'All')  # Credit, Debit, All
    date_from = request.data.get('date_from')  # dd-mm-yyyy
    date_to = request.data.get('date_to')  # dd-mm-yyyy
    page = int(request.data.get('page', 1))

    print(request.data)
    
    # Normalize type filter
    txn_type_lower = txn_type.lower() if txn_type else 'all'
    if txn_type_lower in ['cr', 'credit', 'c']:
        txn_type = 'Credit'
    elif txn_type_lower in ['dr', 'debit', 'd']:
        txn_type = 'Debit'
    else:
        txn_type = 'All'
    
    try:
        user = Users.objects.get(user_id=user_id)
        wallet = Wallet.objects.get(user_id=user)
        
        # Base query
        query = Q(initiated_by=user) | Q(transaction_to=user)
        query &= Q(status='SUCCESSFUL')
        
        # Date filters
        if date_from:
            date_from_obj = datetime.strptime(date_from, '%d-%m-%Y').date()
            query &= Q(transaction_date__date__gte=date_from_obj)
        if date_to:
            date_to_obj = datetime.strptime(date_to, '%d-%m-%Y').date()
            query &= Q(transaction_date__date__lte=date_to_obj)
        
        transactions = Transaction.objects.filter(query).select_related(
            'initiated_by__profile_id', 
            'transaction_to__profile_id',
            'order__product'
        ).order_by('-transaction_date')
        
        # Group by date
        grouped = defaultdict(list)
        for txn in transactions:
            is_credit = txn.transaction_to.user_id == user_id
            
            # Type filter
            if txn_type == 'Credit' and not is_credit:
                continue
            if txn_type == 'Debit' and is_credit:
                continue
            
            date_key = txn.transaction_date.date()
            other_user = txn.initiated_by if is_credit else txn.transaction_to
            
            # Truncate product name to 3 words
            product_name = txn.order.product.name if txn.order and txn.order.product else 'N/A'
            words = product_name.split()
            if len(words) > 3:
                product_name = ' '.join(words[:3]) + '......'
            
            grouped[date_key].append({
                'transaction_id': str(txn.transaction_id),
                'amount': f"{'+ ' if is_credit else '- '}Rs. {txn.amount:,.2f}",
                'type': 'credit' if is_credit else 'debit',
                'for_product': product_name,
                'user_id': str(other_user.user_id),
                'full_name': other_user.get_full_name_from_userModel(),
                'timestamp': txn.transaction_date.strftime('%b %d, %Y | %I:%M %p'),
                'amount_value': txn.amount if is_credit else -txn.amount
            })
        
        # Calculate closing balance for each date
        result = []
        current_balance = Decimal(str(wallet.balance))
        
        for date_key in sorted(grouped.keys(), reverse=True):
            day_transactions = grouped[date_key]
            
            result.append({
                'date': date_key.strftime('%d'),
                'monthYear': date_key.strftime('%b %Y'),
                'closingBalance': f"Rs. {current_balance:,.2f}",
                'transactions': [
                    {k: v for k, v in t.items() if k != 'amount_value'}
                    for t in day_transactions
                ]
            })
            
            # Subtract day's net change to get previous balance
            day_total = sum(Decimal(str(t['amount_value'])) for t in day_transactions)
            current_balance -= day_total
        
        # Pagination
        page_size = 15
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_result = result[start_idx:end_idx]
        
        return Response({
            'data': paginated_result,
            'page': page,
            'total_pages': (len(result) + page_size - 1) // page_size,
            'total_items': len(result)
        }, status=status.HTTP_200_OK)
        
    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Wallet.DoesNotExist:
        return Response({'error': 'Wallet not found'}, status=status.HTTP_404_NOT_FOUND)
    except ValueError:
        return Response({'error': 'Invalid date format. Use dd-mm-yyyy'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

##########################################################################################
#                            Transaction History Grouped by Date End
##########################################################################################
