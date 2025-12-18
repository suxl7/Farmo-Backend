from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from ..models import Users
from ..serializers import UsersSerializer


@api_view(['POST'])
@permission_classes([AllowAny])  # No authentication required for login
def login(request):
    """Login with user_id/phone/email and password, returns JWT tokens"""
    # Get login credentials from request
    identifier = request.data.get('identifier')  # Can be user_id, phone, or email
    password = request.data.get('password')
    
    # Validate required fields
    if not identifier or not password:
        return Response({'error': 'Identifier and password required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from django.db.models import Q
        # Find user by user_id, phone, or email using OR query
        user = Users.objects.get(Q(user_id=identifier) | Q(phone=identifier) | Q(email=identifier))
        
        # Verify password from Credentials model (not Users model)
        if hasattr(user, 'credentials') and user.credentials.password:
            # Check hashed password matches
            if user.credentials.check_password(password):
                # Generate JWT tokens on successful authentication
                refresh = RefreshToken.for_user(user)
                return Response({
                    'user': UsersSerializer(user).data,
                    'refresh': str(refresh),  # For refreshing access tokens
                    'access': str(refresh.access_token),  # For API authentication
                }, status=status.HTTP_200_OK)
        
        # Password verification failed
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    except Users.DoesNotExist:
        # User not found - return same error for security
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


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
