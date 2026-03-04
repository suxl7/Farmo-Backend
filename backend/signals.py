from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from backend.models import Wallet, Transaction, UsersProfile, Users


@receiver(post_save, sender='backend.Users')
def create_user_wallet(sender, instance, created, **kwargs):
	"""Automatically create a wallet when a new user is created"""
	if created and instance.is_admin == False:
		Wallet.objects.create(
			wallet_id=f"W-{instance.user_id}",
			user_id=instance,
			balance=0,
			pin = "0000",
			created_date=timezone.now(),
			is_active=False
		)
	
    	
@receiver(post_save, sender='backend.OrderRequest')
def transaction_created_for_order(sender, instance, created, **kwargs):
	'''Automatically create a transaction when a new order is created'''
	import uuid
	try:
		userid = instance.product.user_id
		payment_method = instance.payment_method

		if instance.order_status == 'ACCEPTED' and payment_method == 'WALLET' and not Transaction.objects.filter(order=instance).exists():
			Transaction.objects.create(
				transaction_id=str(uuid.uuid4()),
				order=instance,
				transaction_to=userid,
				payment_method=payment_method,
				amount=instance.total_cost,
				currency='NRP',
				status='PENDING',
				status_history=[
					{'status': 'PENDING',
		             'time': str(timezone.now())}
					],
				transaction_date=instance.ordered_date,
				created_at=timezone.now(),
				updated_at=None,
				initiated_by= instance.consumer_id
			)
	except Exception as e:
		raise Exception(f"Failed to create transaction.")




@receiver(post_save, sender='backend.Verification')
def update_user_profile_status(sender, instance, created, **kwargs):
	'''Automatically update the user profile status when a new verification is created'''
	u = 'p'