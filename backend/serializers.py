from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import (
    Users, UsersProfile, Wallet, Transaction, Product, ProductMedia,
    ProductRating, FarmerRating, Verification, OrderRequest, OrdProdLink, Tokens
)


class UsersSerializer(serializers.ModelSerializer):
    """Serializer for Users model with password validation"""
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    
    class Meta:
        model = Users
        fields = '__all__'
    
    def create(self, validated_data):
        # Extract password from validated_data to handle hashing separately
        password = validated_data.pop('password', None)
        user = Users.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user
     


class UsersProfileSerializer(serializers.ModelSerializer):
    """Serializer for UsersProfile model"""
    class Meta:
        model = UsersProfile
        fields = '__all__'




class WalletSerializer(serializers.ModelSerializer):
    """Serializer for Wallet model"""
    pin = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Wallet
        fields = '__all__'
        extra_kwargs = {'pin': {'write_only': True}}
    
    def create(self, validated_data):
        pin = validated_data.pop('pin', None)
        wallet = Wallet.objects.create(**validated_data)
        if pin:
            wallet.set_pin(pin)
            wallet.save()
        return wallet



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


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model"""
    class Meta:
        model = Transaction
        fields = '__all__'


class TokensSerializer(serializers.ModelSerializer):
    """Serializer for Tokens model"""
    class Meta:
        model = Tokens
        fields = '__all__'
