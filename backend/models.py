from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.db.models.signals import post_save
from django.dispatch import receiver
import secrets
from django.core.validators import MinValueValidator, MaxValueValidator


class UsersProfile(models.Model):
    """User profile storing detailed user information"""
    profile_id = models.AutoField(primary_key=True)
    profile_url = models.CharField(max_length=255, blank=True, null=True)
    f_name = models.CharField(max_length=50)
    m_name = models.CharField(max_length=50, blank=True, null=True)
    l_name = models.CharField(max_length=50)

    user_type = models.CharField(max_length=50, default='Consumer')
    province = models.CharField(max_length=50, blank=True, null=True)
    district = models.CharField(max_length=50, blank=True, null=True)
    municipal = models.CharField(max_length=50, blank=True, null=True)
    ward = models.CharField(max_length=50, blank=True, null=True)
    tole = models.CharField(max_length=100, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    sex = models.CharField(max_length=20, blank=True, null=True)
    phone02 = models.CharField(max_length=15, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    facebook = models.CharField(max_length=255, blank=True, null=True)
    whatsapp = models.CharField(max_length=15, blank=True, null=True)
    join_date = models.DateTimeField(default=timezone.now)
    about = models.CharField(max_length=50, blank=True, null=True)

    @property
    def get_Address(self):
        province = self.province
        district = self.district
        municipal = self.municipal
        ward = self.ward
        tole = self.tole
        return f"{municipal}-{ward} {tole}, {district}, {province}"


    @property
    def get_Full_Name(self):
        middle_name = self.m_name
        if middle_name != None:
            full_name = f"{self.f_name} {middle_name} {self.l_name}"
        else:
            full_name = f"{self.f_name} {self.l_name}"
        return full_name
    

    @classmethod
    def create_profile(cls, profile_url,f_name, m_name, l_name, user_type, province, district, municipal, ward, tole, dob, sex, phone02, email, facebook, whatsapp, about):
        obj = cls.objects.create(
            profile_url=profile_url,
            f_name=f_name,
            m_name=m_name,
            l_name=l_name,
            user_type=user_type,
            province=province,
            district=district,
            municipal=municipal,
            ward=ward,
            tole=tole,
            dob=dob,
            sex=sex,
            phone02=phone02,
            email=email,
            facebook=facebook,
            whatsapp=whatsapp,
            about=about,
            join_date=timezone.now()
        )
        return obj.profile_id

    def __str__(self):
        return f"{self.f_name} {self.l_name}"

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(user_type__in=['Consumer', 'Farmer', 'VerifiedConsumer', 'VerifiedFarmer', 'Admin', 'SuperAdmin']),
                name='valid_user_type'
            )
        ]

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
    
    def check_pass(self, raw_pass):
        if self.password == raw_pass:
            return True 
        
        return False

    def update_password(self, new_password):
        """Update to a new password"""
        self.password = make_password(new_password)
        self.save(update_fields=['password'])

    @property
    def get_email_from_usersModel(self):
        return self.profile_id.email
    

    def __str__(self):
        return f"User {self.user_id}"


    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(profile_status__in=['PENDING', 'ACTIVATED', 'SUSPENDED', 'DELETED']),
                name='valid_profile_status'
            )
        ]


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


    def __str__(self):
        return f"Wallet {self.wallet_id}: {self.amount}"

    class Meta:
        unique_together = ('wallet_id', 'user_id')



class Product(models.Model):
    """Product model for farmer's agricultural products"""
    p_id = models.AutoField( primary_key=True)
    user_id = models.ForeignKey(Users, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    is_organic = models.BooleanField(default=False)
    quantity_available = models.IntegerField()
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    produced_date = models.DateField()
    registered_at = models.DateTimeField(default=timezone.now)
    expiry_Date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    delivery_option = models.CharField(max_length=100, default='Not-Available')
    product_status = models.CharField(max_length=100,  default='Available')
    

    @classmethod
    def create_product(cls, user_id, name, category, is_organic, quantity_available, cost_per_unit, produced_date, expiry_Date, description, delivery_option):
        """Create a new product"""
        obj = cls.objects.create(
            user_id=user_id,
            name=name,
            category=category,
            is_organic=is_organic,
            quantity_available=quantity_available,
            cost_per_unit=cost_per_unit,
            registered_at=timezone.now(),
            produced_date=produced_date,
            expiry_Date=expiry_Date,
            description=description,
            delivery_option	=delivery_option,
            product_status='AVAILABLE'
        )
        return obj.p_id


    def __str__(self):
        return f"{self.name} ({self.p_id})"

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(delivery_option__in=['Not-Available', 'Available']) & models.Q(product_status__in=['Available', 'Sold', 'Expired']),
                name='valid_product_status_delivery_option'
            )
        ]


class ProductMedia(models.Model):
    """ProductMedia model for product images and videos"""
    media_id = models.AutoField(primary_key=True)
    p_id = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True)
    media_url = models.CharField(max_length=255)
    media_type = models.CharField(max_length=10, blank=True, null=True)

    @classmethod
    def create_media(cls,P_id, media_url, media_type):
        """Create a new media entry"""
        
        obj = cls.objects.create(
            p_id=P_id,
            media_url=media_url,
            media_type=media_type
        )
        return obj.media_id
    
    @property
    def get_media_url(self):
        return self.media_url


    def __str__(self):
        return f"Media {self.media_id}"

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(media_type__in=['image', 'video']),
                name='valid_media_type'
            )
        ]


class ProductRating(models.Model):
    """ProductRating model for product reviews and ratings"""
    ProductRating_id = models.AutoField( primary_key=True)
    p_id = models.ForeignKey(Product, on_delete=models.PROTECT)
    consumer_id = models.ForeignKey(Users, on_delete=models.PROTECT)
    score = models.IntegerField(validators=[MinValueValidator(1),MaxValueValidator(10)])
    comment = models.TextField()
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"ProductRating {self.ProductRating_id}: {self.score}"


class Rating(models.Model):
    """FarmerRating model for farmer reviews by consumers"""
    FarmerRate_id = models.AutoField(primary_key=True)
    farmer_id = models.ForeignKey(Users, on_delete=models.PROTECT, related_name='Farmer')
    consumer_id = models.ForeignKey(Users, on_delete=models.PROTECT, related_name='Consumer')
    score = models.IntegerField(validators=[
            MinValueValidator(1),
            MaxValueValidator(10)
        ])
    comment = models.TextField()

    rated_by = models.CharField(max_length=50, default='Consumer') #

    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Rating {self.FarmerRate_id}: {self.score}"

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rated_by__in=['Farmer', 'Consumer']),
                name='valid_rated_by'
            )
        ]


class Verification(models.Model):
    """Verification model for user identity verification"""
    V_id = models.AutoField( primary_key=True)
    user_id = models.ForeignKey(Users, on_delete=models.PROTECT, db_index=True)
    status = models.CharField(max_length=20, default='PENDING')
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

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=['PENDING', 'VERIFIED', 'REJECTED']),
                name='valid_status'
            )
        ]


class OrderRequest(models.Model):
    """OrderRequest model for customer orders"""
    order_id = models.CharField(max_length=50, primary_key=True)
    consumer_id = models.ForeignKey(Users, on_delete=models.PROTECT)
    ordered_date = models.DateTimeField(default=timezone.now)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    order_status = models.CharField(max_length=20, default='PENDING') # Accepted, Rejected
    shipping_address = models.TextField(blank=True, null=True)
    expected_delivery_date = models.DateField(blank=True, null=True)
    ORDER_OTP = models.CharField(max_length=6, blank=True, null=True)

    @property
    def get_pid_from_orderid(self):
        return OrdProdLink.objects.filter(order_id=self.order_id).values_list('p_id')

    @classmethod
    def create_order(cls, consumer_id, total_cost, shipping_address, expected_delivery_date):
        obj = cls.objects.create(
            consumer_id=consumer_id,
            ordered_date=timezone.now(),
            total_cost=total_cost,
            order_status='PENDING',
            shipping_address=shipping_address,
            expected_delivery_date=expected_delivery_date,
            ORDER_OTP=secrets.token_hex(6).upper()
        )
        return obj.order_id



    def __str__(self):
        return f"Order {self.order_id}: {self.order_status}"

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(order_status__in=['PENDING', 'ACCEPTED', 'REJECTED']),
                name='valid_order_status'
            )
        ]


class OrdProdLink(models.Model):
    """OrdProdLink model linking orders to products with quantities"""
    order_id = models.ForeignKey(OrderRequest, on_delete=models.PROTECT, db_index=True)
    p_id = models.ForeignKey(Product, on_delete=models.PROTECT,db_index=True)
    quantity = models.IntegerField()
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    @classmethod
    def create_OrderProdLink(cls, order_id, p_id, quantity, cost_per_unit):
        cls.objects.create(
            order_id=order_id,
            p_id=p_id,
            quantity=quantity,
            cost_per_unit=cost_per_unit
        )
        return True if cls.objects.filter(order_id=order_id, p_id=p_id).exists() else False

    def __str__(self):
        return f"{self.quantity} x Product {self.P_id} in order {self.order_id}"


    class Meta:
        unique_together = ('order_id', 'p_id')


class Transaction(models.Model):
    transaction_id = models.CharField(primary_key=True, editable=False)
    order = models.ForeignKey(OrderRequest, on_delete=models.PROTECT, db_index=True)
    transaction_to = models.ForeignKey(Wallet, on_delete=models.PROTECT, db_index=True, default=None)
    payment_method = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='NRP')
    status = models.CharField(max_length=20, default='PENDING')
    failure_reason = models.TextField(blank=True, null=True)
    status_history = models.JSONField(blank=True, null=True)
    transaction_date = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    initiated_by = models.ForeignKey(Users, on_delete=models.PROTECT)

    def __str__(self):
        return f'Transaction {self.transaction_id}: {self.status}'

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=['PENDING', 'SUCCESSFUL', 'FAILED', 'REFUNDED']),
                name='valid_status_transaction'
            ),
            models.CheckConstraint(
                condition=models.Q(payment_method__in=['WALLET', 'COD', 'KHALTI', 'ESewa']),
                name='valid_payment_method'
            ),
            models.CheckConstraint(
                condition=models.Q(initiated_by__in=['CUSTOMER', 'ADMIN']),
                name='valid_initiated_by'
            )

        ]



class Tokens(models.Model):
    """Tokens model for JWT token management"""
    user_id = models.ForeignKey(Users, on_delete=models.PROTECT, db_index=True)
    token = models.TextField(db_index=True)
    device_info = models.CharField(max_length=255, blank=True, null=True)
    issued_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    refresh_token = models.TextField(blank=True, null=True)
    token_status = models.CharField(max_length=20, default='ACTIVE')


    @classmethod
    def create_token(cls, user, days=40):
        """Generate a random token and set expiry days ahead"""

        token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        return cls.objects.create(
            user_id=user,
            token=token,
            refresh_token=refresh_token,
            issued_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(days=days),
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

    @property
    def is_active(self):
        """Check if the token is still active"""
        return self.token_status == 'ACTIVE' and not self.is_expired

    @property
    def is_expired(self):
        """Check if the token has expired"""
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Token for {self.user_id}"

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(token_status__in=['ACTIVE', 'INACTIVE', 'SUSPENDED']),
                name='valid_token_status'
            )
        ]


class UserActivity(models.Model):
    """Track main user activities """
    activity_id = models.CharField(max_length=50, primary_key=True)
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=50, blank=True, null=True)   # e.g. LOGIN, LOGOUT, PRODUCT_UPLOAD, ORDER_PLACED
    description = models.TextField(blank=True, null=True)  # optional details
    timestamp = models.DateTimeField(default=timezone.now)

    @classmethod
    def create_activity(cls, user, activity, discription):
        """Create a new activity record"""
        cls.objects.create(
            activity_id=secrets.token_urlsafe(32),
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
    status = models.CharField(max_length=20, default="PENDING")
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.user_id} -> {self.target_user.user_id} ({self.status})"


    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=['PENDING', 'ACCEPTED', 'BLOCKED']),
                name='valid_status_connection'
            ),
            models.UniqueConstraint(
                fields=['user', 'target_user'], 
                name='unique_user_connection'
            )
        ]


class PaymentMethodAccepts(models.Model):
    """Track accepted payment methods for each user"""
    pm_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE)
    payment_method = models.JSONField(max_length=50, default=list, blank=True) # e.g. WALLET, COD, KHALTI, ESEWA

    @property
    def get_payment_methods(self):
        """Get the list of accepted payment methods for this user"""
        return self.payment_method
    
    def __str__(self):
        return f"{self.user_id} - {self.payment_method} ({'Active' if self.is_active else 'Inactive'})"
    


class OTP(models.Model):
    """Track OTPs for user authentication"""
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    otp_type = models.CharField(max_length=20, default='LOGIN')
    otp_status = models.CharField(max_length=20, default='ACTIVE')
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.user_id} - {self.otp_type} ({self.otp_status})"


    @property
    def get_OTP(self):
        return self.otp
    
    @property
    def is_expired(self):
        """Check if the OTP has expired"""
        return timezone.now() > self.expires_at


    @property
    def effective_status_OTP(self):
        """Check if the OTP is still active"""
        if self.otp_status == 'ACTIVE' and not self.is_expired():
            return 'ACTIVE'
        elif self.is_expired and self.otp_status == 'ACTIVE':
            self.otp_status = 'EXPIRED'
            self.save(update_fields=['otp_status'])
            return 'EXPIRED'
        elif self.otp_status == 'USED':
            return 'USED'
        elif self.otp_status == 'EXPIRED':
            return 'EXPIRED'
        
    
    @classmethod
    def create_otp(cls, user, otp, otp_type, created_at,expires_in=2):
        """Create a new OTP"""
        return cls.objects.create(
            user_id=user,
            otp=otp,
            otp_type=otp_type,
            otp_status='ACTIVE',
            created_at=created_at,
            expires_at=timezone.now() + timezone.timedelta(minutes=expires_in)
        )


    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(otp_status__in=['ACTIVE', 'USED', 'EXPIRED']),
                name='valid_otp_status'
            )
        ]