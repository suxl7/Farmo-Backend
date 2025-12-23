from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from ..models import Users, Tokens
from ..serializers import UsersSerializer
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
import secrets
from backend.utils.update_activity import update_activity


# Helper function to manage tokens [check, generate, save, deactivate old if needed]
def check_generate_save_new_token(user, device_info):
    # Step 1: Get all active tokens for this user
    active_tokens = Tokens.objects.filter(
        user_id=user,
        token_status="ACTIVE"
    ).order_by("issued_at")  # oldest first

    # Step 2: If already 2 active tokens, deactivate the oldest one
    # if active tokens are less than 2 then do nothing
    if active_tokens.count() >= 2:
        oldest_token = active_tokens.first()
        oldest_token.token_status = "INACTIVE"
        oldest_token.save(update_fields=["token_status"])
    
    if user.is_admin:
        expiration_delta = timedelta(hours=12)  # Admin tokens valid for 12 hours
    else:
        expiration_delta = timedelta(days=40)
    
    # Step 3: Create the new token
    new_token = Tokens.objects.create(
        user_id=user,
        token=secrets.token_urlsafe(32),
        refresh_token=secrets.token_urlsafe(32),
        device_info=device_info,
        issued_at=timezone.now(),
        expires_at=timezone.now() + expiration_delta,  # example expiry
        token_status="ACTIVE"
    )
    return new_token


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    First Login: Login with identifier and password, returns tokens
    User sends: identifier (userID or Phone), password, is_admin, device_info
    Server returns: login_access, token, refresh_token, user_id (and user data)
    """
    identifier = request.data.get('identifier')
    password = request.data.get('password')
    is_admin = request.data.get('is_admin', False)
    device_info = request.data.get('device_info', '')
    
    if not identifier or not password:
        return Response({
            'login_access': False,
            'error_code': 'MISSING_CREDENTIALS'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Search user by userID or Phone and is_admin status
        user = Users.objects.get(Q(user_id=identifier) | Q(phone=identifier), is_admin=is_admin)
        
        # Verify password
        if not user.check_password(password):
            return Response({
                'login_access': False,
                'error_code': 'INVALID_CREDENTIALS'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check profile status
        if user.profile_status == 'PENDING':
            return Response({
                'login_access': False,
                'error_code': 'ACCOUNT_PENDING'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.profile_status != 'ACTIVE':
            return Response({
                'login_access': False,
                'error_code': 'ACCOUNT_INACTIVE'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate tokens and manage active tokens
        token_obj = check_generate_save_new_token(user, device_info)
        token = token_obj.token
        refresh_token = token_obj.refresh_token
        
        # Update last activity
        update_activity(user, activity="LOGIN", discription="")
        
        # Return response according to documentation
        return Response({
            'login_access': True,  # Changed from login_access
            'token': token,
            'refresh_token': refresh_token,
            'user_id': user.user_id
        }, status=status.HTTP_200_OK)
        
    except Users.DoesNotExist:
        return Response({
            'login_access': False,
            'error_code': 'INVALID_CREDENTIALS'
        }, status=status.HTTP_401_UNAUTHORIZED)



@api_view(['POST'])
@permission_classes([AllowAny])
def login_with_token(request):
    """
    Second Login (Remember Me): Login with token, refresh_token and user_id
    Used when user has "remember me" enabled
    User sends: token, refresh_token, user_id
    Server returns: login_access = True (if token valid) OR new tokens (if expired)
    """
    token = request.data.get('token')
    user_id = request.data.get('user_id')
    refresh_token = request.data.get('refresh_token')
    device_info = request.data.get('device_info')
    
    if not token or not user_id or not refresh_token:
        return Response({
            'login_access': False,
            'error_code': 'MISSING_TOKENS_OR_USERID'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Find token entry in database
        token_entry = Tokens.objects.get(
            token=token,
            user_id__user_id=user_id,
            refresh_token=refresh_token,
            device_info=device_info
        )
        
        user = token_entry.user_id
        
        # Check profile status
        if user.profile_status == 'PENDING':
            return Response({
                'login_access': False,
                'error_code': 'ACCOUNT_PENDING', 
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.profile_status != 'ACTIVE':
            return Response({
                'login_access': False,
                'error_code': 'ACCOUNT_INACTIVE'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if token is expired (after 40 days)
        current_time = timezone.now()
        
        if current_time > token_entry.expires_at:
            # Token expired but present - generate new tokens using refresh_token
            new_token_obj = check_generate_save_new_token(user, device_info) 
            new_token = new_token_obj.token
            new_refresh_token = new_token_obj.refresh_token
            
            update_activity(user, activity="LOGIN", discription="")
            
            # Return new tokens
            return Response({
                'login_access': True,
                'token': new_token,
                'refresh_token': new_refresh_token,
                'user_id': user.user_id
            }, status=status.HTTP_200_OK)
        
        else:
            # Token still valid - just grant access
            update_activity(user, activity="LOGIN", discription="")
            
            # According to doc: Second time login returns no new tokens
            return Response({
                'login_access': True,
                'token' : token,
                'refresh_token': refresh_token,
                'user_id': user.user_id
            }, status=status.HTTP_200_OK)
        
    except Tokens.DoesNotExist:
        return Response({
            'login_access': False,
            'error_code': 'INVALID_TOKENS'
        }, status=status.HTTP_401_UNAUTHORIZED)



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

