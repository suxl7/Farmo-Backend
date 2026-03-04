from backend.models import Users, OrderRequest, Wallet, Transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.permissions import HasValidTokenForUser, IsAdmin
from django.db.models import *
from django.utils import timezone

##########################################################################################
#                            Transfer fund Start
##########################################################################################

def transfer_fund(order, paid_amount_by_wallet):
    try:
        
        transaction = Transaction.objects.get(order=order)
        if transaction.status == 'SUCCESSFUL':
            raise Exception('Transaction already completed')

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


##########################################################################################
#                            Transfer hiatory End
##########################################################################################
