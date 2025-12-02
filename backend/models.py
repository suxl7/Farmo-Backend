from django.db import models
from django.utils import timezone


class Users(models.Model):
	full_name = models.CharField(max_length=200)
	email = models.EmailField(unique=True)
	phone = models.CharField(max_length=30, blank=True, null=True)
	is_farmer = models.BooleanField(default=False)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(default=timezone.now)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.full_name} <{self.email}>"


class Credentials(models.Model):
	user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='credentials')
	password_hash = models.CharField(max_length=255)
	otp = models.CharField(max_length=50, blank=True, null=True)
	last_login = models.DateTimeField(blank=True, null=True)

	def __str__(self):
		return f"Credentials for {self.user.email}"


class Wallet(models.Model):
	user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='wallet')
	balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	currency = models.CharField(max_length=10, default='USD')

	def __str__(self):
		return f"Wallet({self.user.email}): {self.balance} {self.currency}"


class Transaction(models.Model):
	TX_TYPES = (("credit", "Credit"), ("debit", "Debit"))
	STATUS = (("pending", "Pending"), ("done", "Done"), ("failed", "Failed"))

	wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	tx_type = models.CharField(max_length=10, choices=TX_TYPES)
	status = models.CharField(max_length=10, choices=STATUS, default='pending')
	reference = models.CharField(max_length=200, blank=True, null=True)
	created_at = models.DateTimeField(default=timezone.now)

	def __str__(self):
		return f"{self.tx_type} {self.amount} ({self.status}) for {self.wallet.user.email}"


class Product(models.Model):
	owner = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='products')
	title = models.CharField(max_length=255)
	description = models.TextField(blank=True)
	price = models.DecimalField(max_digits=10, decimal_places=2)
	quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
	unit = models.CharField(max_length=50, default='kg')
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(default=timezone.now)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.title} ({self.owner.email})"


class ProductMedia(models.Model):
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='media')
	media_url = models.CharField(max_length=1024)
	is_primary = models.BooleanField(default=False)

	def __str__(self):
		return f"Media for {self.product.title} ({'primary' if self.is_primary else 'secondary'})"


class ProductRating(models.Model):
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
	rater = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, related_name='product_ratings')
	rating = models.PositiveSmallIntegerField()
	comment = models.TextField(blank=True)
	created_at = models.DateTimeField(default=timezone.now)

	def __str__(self):
		return f"Rating {self.rating} for {self.product.title}"


class FarmerRating(models.Model):
	farmer = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='farmer_ratings')
	rater = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, related_name='given_farmer_ratings')
	rating = models.PositiveSmallIntegerField()
	comment = models.TextField(blank=True)
	created_at = models.DateTimeField(default=timezone.now)

	def __str__(self):
		return f"FarmerRating {self.rating} for {self.farmer.email}"


class Verification(models.Model):
	user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='verification')
	is_verified = models.BooleanField(default=False)
	document_url = models.CharField(max_length=1024, blank=True, null=True)
	verified_at = models.DateTimeField(blank=True, null=True)

	def __str__(self):
		return f"Verification({self.user.email}): {self.is_verified}"


class OrderRequest(models.Model):
	buyer = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='orders')
	status = models.CharField(max_length=50, default='pending')
	total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	created_at = models.DateTimeField(default=timezone.now)

	def __str__(self):
		return f"Order {self.id} by {self.buyer.email} ({self.status})"


class OrdProdLink(models.Model):
	order = models.ForeignKey(OrderRequest, on_delete=models.CASCADE, related_name='order_items')
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	quantity = models.DecimalField(max_digits=10, decimal_places=3, default=1)
	price = models.DecimalField(max_digits=10, decimal_places=2)

	def __str__(self):
		return f"{self.quantity} x {self.product.title} in order {self.order.id}"

