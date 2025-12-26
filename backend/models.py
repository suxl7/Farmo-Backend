from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.db.models.signals import post_save
from django.dispatch import receiver


class UsersProfile(models.Model):
	"""User profile storing detailed user information"""
	profile_id = models.CharField(max_length=20, primary_key=True)
	profile_url = models.CharField(max_length=255, blank=True, null=True)
	f_name = models.CharField(max_length=50)
	m_name = models.CharField(max_length=50, blank=True, null=True)
	l_name = models.CharField(max_length=50)
	user_type = models.CharField(max_length=50)
	province = models.CharField(max_length=50, blank=True, null=True)
	district = models.CharField(max_length=50, blank=True, null=True)
	municipal = models.CharField(max_length=50, blank=True, null=True)
	ward = models.CharField(max_length=50, blank=True, null=True)
	tole = models.CharField(max_length=100, blank=True, null=True)
	dob = models.DateField(blank=True, null=True)
	sex = models.CharField(max_length=20, blank=True, null=True)
	phone02 = models.CharField(max_length=15, blank=True, null=True)
	email = models.CharField(max_length=100, null=True)
	facebook = models.CharField(max_length=255, blank=True, null=True)
	whatsapp = models.CharField(max_length=15, blank=True, null=True)
	join_date = models.DateTimeField(default=timezone.now)
	about = models.CharField(max_length=50, blank=True, null=True)


	def __str__(self):
		return f"{self.f_name} {self.l_name}"

class Users(models.Model):
	"""User model storing basic user information"""
	user_id = models.CharField(max_length=20, primary_key=True)
	phone = models.CharField(max_length=15, blank=True)
	password = models.CharField(max_length=128)
	profile_status = models.CharField(max_length=20, default='ACTIVATED')
	is_admin = models.BooleanField(default=False)
	profile_id = models.ForeignKey(UsersProfile, on_delete=models.PROTECT)

	def set_password(self, raw_password):
		"""Hash and store password securely"""
		self.password = make_password(raw_password)

	def check_password(self, raw_password):
		"""Verify password against stored hash"""
		return check_password(raw_password, self.password)
	
	def update_password(self, new_password):
		"""Update to a new password"""
		self.password = make_password(new_password)
		self.save(update_fields=['password'])

	def __str__(self):
		return f"User {self.user_id}"


class Wallet(models.Model):
	"""Wallet model for user balance and PIN management"""
	wallet_id = models.CharField(max_length=50, primary_key=True)
	user_id = models.ForeignKey(Users, on_delete=models.PROTECT)
	amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
	pin = models.CharField(max_length=128)
	created_date = models.DateTimeField(default=timezone.now)
	is_active = models.BooleanField(default=False)


	def set_pin(self, raw_pin):
		"""Hash the 4-digit PIN before saving"""
		if len(raw_pin) != 4 or not raw_pin.isdigit():
			raise ValueError("PIN must be exactly 4 digits.")
		self.pin = make_password(raw_pin)

	def check_pin(self, raw_pin):
		"""Verify entered PIN against stored hash"""
		return check_password(raw_pin, self.pin)
	
	def update_pin(self, new_pin):
		"""Update the PIN"""
		if len(new_pin) != 4 or not new_pin.isdigit():
			raise ValueError("PIN must be exactly 4 digits.")
		self.pin = make_password(new_pin)
		self.save(update_fields=['pin'])
	
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

	def __str__(self):
		return f"Wallet {self.wallet_id}: {self.amount}"


class ProductMedia(models.Model):
	"""ProductMedia model for product images and videos"""
	media_id = models.AutoField(primary_key=True)
	media_url = models.CharField(max_length=255)
	media_type = models.CharField(max_length=10, blank=True, null=True)

	def __str__(self):
		return f"Media {self.media_id}"


class Product(models.Model):
	"""Product model for farmer's agricultural products"""
	P_id = models.CharField(max_length=50, primary_key=True)
	user_id = models.ForeignKey(Users, on_delete=models.PROTECT)
	media_id = models.ForeignKey(ProductMedia, on_delete=models.PROTECT)
	name = models.CharField(max_length=255)
	category = models.CharField(max_length=100)
	is_organic = models.BooleanField(default=False)
	quantity_available = models.IntegerField()
	cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
	produced_date = models.DateField()
	registered_date = models.DateTimeField(default=timezone.now)
	expiry_Date = models.DateField(null=True, blank=True)
	description = models.TextField(blank=True, null=True)
	delivery_option = models.CharField(max_length=100, default='not-available')
	product_status = models.CharField(max_length=100, default='AVAILABLE')

	def __str__(self):
		return f"{self.name} ({self.p_id})"


class ProductRating(models.Model):
	"""ProductRating model for product reviews and ratings"""
	PRating_id = models.CharField(max_length=50, primary_key=True)
	P_id = models.ForeignKey(Product, on_delete=models.PROTECT)
	consumer_id = models.ForeignKey(Users, on_delete=models.PROTECT)
	score = models.IntegerField()
	comment = models.TextField()
	date = models.DateTimeField(default=timezone.now)

	def __str__(self):
		return f"Rating {self.PRating_id}: {self.score}"


class FarmerRating(models.Model):
	"""FarmerRating model for farmer reviews by consumers"""
	R_id = models.CharField(max_length=50, primary_key=True)
	Farmer_id = models.ForeignKey(Users, on_delete=models.PROTECT, related_name='Farmer')
	Consumer_id = models.ForeignKey(Users, on_delete=models.PROTECT, related_name='Consumer')
	score = models.IntegerField()
	comment = models.TextField()
	date = models.DateTimeField(default=timezone.now)

	def __str__(self):
		return f"FarmerRating {self.R_id}: {self.score}"


class Verification(models.Model):
	"""Verification model for user identity verification"""
	V_id = models.CharField(max_length=50, primary_key=True)
	user_id = models.ForeignKey(Users, on_delete=models.PROTECT)
	status = models.CharField(max_length=20, default='Pending')
	id_Type = models.CharField(max_length=50, blank=True, null=True)
	id_Number = models.CharField(max_length=50, blank=True, null=True)
	id_front = models.CharField(max_length=50, blank=True, null=True)
	id_back = models.CharField(max_length=50, blank=True, null=True)
	Selfie_with_id = models.CharField(max_length=50, blank=True, null=True)
	submission_date = models.DateTimeField(default=timezone.now)
	approved_date = models.DateTimeField(blank=True, null=True)
	approved_by = models.CharField(max_length=50, blank=True, null=True)

	def __str__(self):
		return f"Verification {self.V_id}: {self.status}"


class OrderRequest(models.Model):
	"""OrderRequest model for customer orders"""
	order_id = models.CharField(max_length=50, primary_key=True)
	user_id = models.ForeignKey(Users, on_delete=models.PROTECT)
	order_date = models.DateTimeField(default=timezone.now)
	total_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	fullfilment_status = models.CharField(max_length=20, default='PLACED')
	shipping_address = models.TextField(blank=True, null=True)
	expected_delivery_date = models.DateField(blank=True, null=True)

	def __str__(self):
		return f"Order {self.order_id}: {self.fullfilment_status}"


class OrdProdLink(models.Model):
	"""OrdProdLink model linking orders to products with quantities"""
	order_id = models.ForeignKey(OrderRequest, on_delete=models.PROTECT)
	P_id = models.ForeignKey(Product, on_delete=models.PROTECT)
	quantity = models.IntegerField()
	price_at_sale = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

	class Meta:
		unique_together = ('order_id', 'P_id')

	def __str__(self):
		return f"{self.quantity} x Product {self.P_id} in order {self.order_id}"
	

class Transaction(models.Model):
	"""Transaction model for payment records"""
	transaction_id = models.CharField(max_length=50, primary_key=True)
	order_id = models.ForeignKey(OrderRequest, on_delete=models.PROTECT)
	payment_method = models.CharField(max_length=50)
	transaction_id_gateway = models.CharField(max_length=100, blank=True, null=True)
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	status = models.CharField(max_length=20, default='PENDING')
	transaction_date = models.DateTimeField(default=timezone.now)

	def __str__(self):
		return f"Transaction {self.transaction_id}: {self.amount}"


class Tokens(models.Model):
	"""Tokens model for JWT token management"""
	user_id = models.ForeignKey(Users, on_delete=models.CASCADE)
	token = models.TextField()
	device_info = models.CharField(max_length=255, blank=True, null=True)
	issued_at = models.DateTimeField(default=timezone.now)
	expires_at = models.DateTimeField()
	refresh_token = models.TextField(blank=True, null=True)
	token_status = models.CharField(max_length=20, default='ACTIVE')

	@classmethod
	def create_token(cls, user, days=40):
		"""Generate a random token and set expiry days ahead"""
		import secrets
		from datetime import timedelta
		token = secrets.token_urlsafe(32)
		refresh_token = secrets.token_urlsafe(32)
		return cls.objects.create(
			user_id=user,
			token=token,
			refresh_token=refresh_token,
			issued_at=timezone.now(),
			expires_at=timezone.now() + timedelta(days=days),
			token_status='ACTIVE'
		)

	def suspend(self):
		"""Suspend this token"""
		self.token_status = 'SUSPENDED'
		self.save(update_fields=['token_status'])

	def deactivate(self):
		"""Deactivate this token"""
		self.token_status = 'INACTIVE'
		self.save(update_fields=['token_status'])

	def activate(self):
		"""Reactivate this token"""
		self.token_status = 'ACTIVE'
		self.save(update_fields=['token_status'])

	@classmethod
	def deactivate_all_user_tokens(cls, user):
		"""Deactivate all tokens for a user (logout all devices)"""
		cls.objects.filter(user_id=user, token_status='ACTIVE').update(token_status='INACTIVE')

	def __str__(self):
		return f"Token for {self.user_id}"


class UserActivity(models.Model):
    """Track main user activities """
    activity_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=50, blank=True, null=True)   # e.g. LOGIN, LOGOUT, PRODUCT_UPLOAD, ORDER_PLACED
    description = models.TextField(blank=True, null=True)  # optional details
    timestamp = models.DateTimeField(default=timezone.now)

    @classmethod
    def create_activity(cls, user, activity, discription):
        """Create a new activity record"""
        cls.objects.create(
            user_id=user,
            activity_type=activity,
            description=discription,
            timestamp=timezone.now()
        )

    def __str__(self):
        return f"{self.user_id} - {self.activity_type} at {self.timestamp}"

class Connections(models.Model):
    """Track user-to-user connections (mutual or pending)"""
    connection_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="connections")
    target_user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="connected_to")
    status = models.CharField(max_length=20, default="PENDING")  # PENDING, ACCEPTED, BLOCKED
    created_at = models.DateTimeField(default=timezone.now)
	
    class Meta: # Means that a user cannot have multiple connection records with the same target user
        unique_together = ("user", "target_user")

    def __str__(self):
        return f"{self.user.user_id} -> {self.target_user.user_id} ({self.status})"