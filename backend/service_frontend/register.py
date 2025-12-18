from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from backend.serializers import UsersSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from backend.models import Users

@api_view(['GET'])
@permission_classes([AllowAny])
def check_userid(request):
    """Check if userID is available during registration"""
    user_id = request.GET.get('user_id')
    if not user_id:
        return Response({'error': 'user_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
    
    """Check existence of user_id in Users model [exists is boolean]"""
    exists = Users.objects.filter(user_id=user_id).exists()
    return Response({'status': 1 if exists else 0})


@api_view(['POST'])
@permission_classes([AllowAny])  # No authentication required for registration
def register(request):
    """Register new user and return JWT tokens"""
    # Validate incoming user data
    serializer = UsersSerializer(data=request.data)
    if serializer.is_valid():
        # Create new user in database
        user = serializer.save()
        # Generate JWT tokens for immediate login after registration
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UsersSerializer(user).data,
            'refresh': str(refresh),  # Long-lived token for getting new access tokens
            'access': str(refresh.access_token),  # Short-lived token for API requests
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
