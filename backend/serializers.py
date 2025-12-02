from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import (
    Users, Credentials, Wallet, Transaction, Product, ProductMedia,
    ProductRating, FarmerRating, Verification, OrderRequest, OrdProdLink
)


class UsersSerializer(serializers.ModelSerializer):
    """Serializer for Users model with password validation"""
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    
    class Meta:
        model = Users
        fields = '__all__'
     


class CredentialsSerializer(serializers.ModelSerializer):
    """Serializer for Credentials model with password hashing"""
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Credentials
        fields = '__all__'
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        """Create new credential with hashed password"""
        # Extract password from data to hash it separately
        password = validated_data.pop('password')
        # Create credential record without password
        credential = Credentials.objects.create(**validated_data)
        # Hash and set password using secure method
        credential.set_password(password)
        credential.save()
        return credential


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for Wallet model with PIN hashing"""
    pin = serializers.CharField(write_only=True, required=False, min_length=4, max_length=6)

    class Meta:
        model = Wallet
        fields = '__all__'
        extra_kwargs = {'pin': {'write_only': True}}

    def create(self, validated_data):
        """Create new wallet with optional hashed PIN"""
        # Extract PIN from data if provided
        pin = validated_data.pop('pin', None)
        # Create wallet record
        wallet = Wallet.objects.create(**validated_data)
        # Hash and set PIN if provided
        if pin:
            wallet.set_pin(pin)
            wallet.save()
        return wallet

    def update(self, instance, validated_data):
        """Update wallet fields and optionally change PIN"""
        # Extract PIN from data if provided
        pin = validated_data.pop('pin', None)
        # Update all other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        # Hash and update PIN if new one provided
        if pin:
            instance.set_pin(pin)
        instance.save()
        return instance


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model"""
    class Meta:
        model = Transaction
        fields = '__all__'


class ProductMediaSerializer(serializers.ModelSerializer):
    """Serializer for ProductMedia model"""
    class Meta:
        model = ProductMedia
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model with nested media"""
    media = ProductMediaSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = '__all__'


class ProductRatingSerializer(serializers.ModelSerializer):
    """Serializer for ProductRating model"""
    class Meta:
        model = ProductRating
        fields = '__all__'


class FarmerRatingSerializer(serializers.ModelSerializer):
    """Serializer for FarmerRating model"""
    class Meta:
        model = FarmerRating
        fields = '__all__'


class VerificationSerializer(serializers.ModelSerializer):
    """Serializer for Verification model"""
    class Meta:
        model = Verification
        fields = '__all__'


class OrdProdLinkSerializer(serializers.ModelSerializer):
    """Serializer for OrdProdLink model"""
    class Meta:
        model = OrdProdLink
        fields = '__all__'


class OrderRequestSerializer(serializers.ModelSerializer):
    """Serializer for OrderRequest model with nested order items"""
    order_items = OrdProdLinkSerializer(many=True, read_only=True)
    
    class Meta:
        model = OrderRequest
        fields = '__all__'
