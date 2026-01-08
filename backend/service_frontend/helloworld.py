# from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from backend.permissions import HasValidTokenForUser
from ..models import Users, Tokens, UserActivity, OTPs
# from ..serializers import UsersSerializer
from django.utils import timezone
# from datetime import timedelta
from django.db.models import Q
from backend.utils.dataVerifier import *
from backend.utils.smallerServiceHandler import get_half_email
from ..utils.otpAndEmailService import send_otp_to_email


@api_view(['GET'])
@permission_classes([AllowAny])
def hello(request):
    return Response({
        'message': 'Hello, World!'
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def login2(request):
    user = request.data.get('identifier')
    password = request.data.get('password')
    print(user)
    print(password)
    if user == "USR001" and password == "#Apple123":
        return Response({
        'token': '123456',
        'refresh_token': '123456',
        'user_id': 'USR001'
        }, status=status.HTTP_200_OK)
    
    return Response({
        'message' : 'Error Login'
    }, status=status.HTTP_401_UNAUTHORIZED)
    