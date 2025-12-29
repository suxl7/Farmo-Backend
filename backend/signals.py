from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from backend.models import Wallet

@receiver(post_save, sender='backend.Users')
def create_user_wallet(sender, instance, created, **kwargs):
	"""Automatically create a wallet when a new user is created"""
	if created and instance.is_admin == False:
		Wallet.objects.create(
			wallet_id=f"wallet_{instance.user_id}",
			user_id=instance,
			amount=0.00,
			created_date=timezone.now(),
			is_active=False
		)
	
    	
@receiver(post_save, sender='backend.OrderRequest')
def send_orderRequested_Notification(sender, instance, created, **kwargs):
	"""Automatically create a wallet when a new user is created"""
	message = 'message'