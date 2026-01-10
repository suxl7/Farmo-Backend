from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from backend.models import Wallet, Transaction, PaymentMethodAccepts


@receiver(post_save, sender='backend.Users')
def create_user_wallet(sender, instance, created, **kwargs):
	"""Automatically create a wallet when a new user is created"""
	if created and instance.is_admin == False:
		Wallet.objects.create(
			wallet_id=f"W-{instance.user_id}",
			user_id=instance,
			amount=0.00,
			created_date=timezone.now(),
			is_active=False
		)
	
    	
@receiver(post_save, sender='backend.OrderRequest')
def transaction_created_for_order(sender, instance, created, **kwargs):
	'''Automatically create a transaction when a new order is created'''
	userid = instance.get_pid_from_orderid[0].user_id
	farmer_wallet = Wallet.objects.get(user_id=userid)
	payment_method_accepted = PaymentMethodAccepts.objects.get(user_id=userid).payment_method

	if instance.order_status == 'ACCEPTED':
		Transaction.objects.create(
			transaction_id=f'T-{instance.order_id}',
			order=instance,
			Tranaction_to=farmer_wallet,
			payment_method= payment_method_accepted,
			amount=instance.total_cost,
			currency='NRP',
			status='PENDING',
			status_history=[
				{'status': 'PENDING',
	             'time': timezone.now()}
				],
			transaction_date=instance.ordered_date,
			created_at=timezone.now(),
			updated_at=None,
			initiated_by= instance.consumer_id
		)


@receiver(post_save, sender='backend.Verification')
def update_user_profile_status(sender, instance, created, **kwargs):
	'''Automatically update the user profile status when a new verification is created'''
	u = 'p'