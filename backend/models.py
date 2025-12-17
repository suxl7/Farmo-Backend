from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password



class UsersProfile(models.Model):
	"""User profile storing detailed user information"""
	profile_id = models.CharField(max_length=20, primary_key=True)
	f_name = models.CharField(max_length=50)
	m_name = models.CharField(max_length=50, blank=True, null=True)
	l_name = models.CharField(max_length=50)
	user_type = models.CharField(max_length=50)
	province = models.CharField(max_length=50, blank=True, null=True)
	district = models.CharField(max_length=50, blank=True, null=True)
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
	is_active = models.BooleanField()
	is_admin = models.BooleanField()
	profile_id = models.ForeignKey(UsersProfile, on_delete=models.PROTECT)

	def set_password(self, raw_password):
		"""Hash and store password securely"""
		self.password = make_password(raw_password)

	def check_password(self, raw_password):
		"""Verify password against stored hash"""
		return check_password(raw_password, self.password)

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
	Farmer_id = models.ForeignKey(Users, on_delete=models.PROTECT)
	Consumer_id = models.ForeignKey(Users, on_delete=models.PROTECT)
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
