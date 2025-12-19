from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from ..models import Users, Tokens
from ..serializers import UsersSerializer
from django.utils import timezone
from datetime import timedelta
import secrets


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login with identifier and password, returns tokens"""
    identifier = request.data.get('identifier')
    password = request.data.get('password')
    is_admin = request.data.get('is_admin', False)
    device_info = request.data.get('device_info', '')
    
    if not identifier or not password:
        return Response({'error': 'Identifier and password required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from django.db.models import Q
        user = Users.objects.get(Q(user_id=identifier) | Q(phone=identifier))
        
        if user.is_admin != is_admin:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if user.check_password(password):
            token = secrets.token_urlsafe(32)
            refresh_token = secrets.token_urlsafe(32)
            issued_at = timezone.now()
            expires_at = issued_at + timedelta(days=40)
            
            Tokens.objects.create(
                user_id=user,
                token=token,
                device_info=device_info,
                issued_at=issued_at,
                expires_at=expires_at,
                refresh_token=refresh_token
            )
            
            return Response({
                'user': UsersSerializer(user).data,
                'token': token,
                'refresh_token': refresh_token,
            }, status=status.HTTP_200_OK)
        
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    except Users.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token_view(request):
    """Refresh expired token using refresh_token"""
    user_id = request.data.get('user_id')
    token = request.data.get('token')
    refresh_token = request.data.get('refresh_token')
    device_info = request.data.get('device_info', '')
    
    if not user_id or not token or not refresh_token:
        return Response({'error': 'user_id, token and refresh_token required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        token_obj = Tokens.objects.get(user_id__user_id=user_id, token=token, refresh_token=refresh_token)
        
        if token_obj.expires_at > timezone.now():
            return Response({'message': 'Token still valid', 'token': token, 'refresh_token': refresh_token}, status=status.HTTP_200_OK)
        
        new_token = secrets.token_urlsafe(32)
        new_refresh_token = secrets.token_urlsafe(32)
        new_expires_at = timezone.now() + timedelta(days=40)
        
        token_obj.token = new_token
        token_obj.refresh_token = new_refresh_token
        token_obj.expires_at = new_expires_at
        token_obj.issued_at = timezone.now()
        token_obj.device_info = device_info
        token_obj.save()
        
        return Response({
            'token': new_token,
            'refresh_token': new_refresh_token,
        }, status=status.HTTP_200_OK)
        
    except Tokens.DoesNotExist:
        return Response({'error': 'Invalid token or refresh_token'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])  # Requires JWT authentication (default)
def verify_wallet_pin(request):
    """Verify wallet PIN for authenticated user before transactions"""
    # Get wallet ID and PIN from request
    wallet_id = request.data.get('wallet_id')
    pin = request.data.get('pin')
    
    # Validate required fields
    if not wallet_id or not pin:
        return Response({'error': 'Wallet ID and PIN required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from ..models import Wallet
        # Ensure wallet belongs to authenticated user (security check)
        wallet = Wallet.objects.get(wallet_id=wallet_id, user=request.user)
        # Verify hashed PIN matches
        if wallet.check_pin(pin):
            return Response({'verified': True}, status=status.HTTP_200_OK)
        # PIN verification failed
        return Response({'error': 'Invalid PIN'}, status=status.HTTP_401_UNAUTHORIZED)
    except Wallet.DoesNotExist:
        # Wallet not found or doesn't belong to user
        return Response({'error': 'Wallet not found'}, status=status.HTTP_404_NOT_FOUND)
