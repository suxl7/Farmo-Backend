from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from backend.permissions import HasValidTokenForUser, IsAdmin
from rest_framework.response import Response
from rest_framework import status
from backend.models import Users, Wallet, Transaction
from backend.serializers import VerificationSerializer as VS
import secrets
from django.utils import timezone
from django.utils.crypto import get_random_string
from backend.utils.media_handler import FileManager
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from backend.service_frontend.serviceHome import  get_todays_income, get_todays_expense

##########################################################################################
#                            req_own_wallet Start
##########################################################################################

@api_view(['POST'])
@permission_classes([AllowAny])
#@permission_classes([HasValidTokenForUser])
def req_own_wallet(request):
    user_id = request.headers.get('user-id')
    user = Users.objects.get(user_id=user_id)
    try:
        wallet = Wallet.objects.get(user_id=user)
        if not wallet.is_active:
            return Response({'error': 'Wallet is not active'}, status=status.HTTP_400_BAD_REQUEST)
        if user.profile_id.user_type in ['Farmer', 'VerifiedFarmer']:
            resp = {
                'wallet_id': wallet.wallet_id,
                'balance': wallet.balance,
                'todays_income': get_todays_income(user),
                'todays_expense': get_todays_expense(user)
            }
        elif user.profile_id.user_type in ['Consumer', 'VerifiedConsumer']:
            resp = {
                'wallet_id': wallet.wallet_id,
                'balance': wallet.balance,
                'todays_expense': get_todays_expense(user)
            }
        else:
            return Response({'error': 'Forbidden User'}, status=status.HTTP_403_FORBIDDEN)

        return Response(resp, status=status.HTTP_200_OK)
    
    except Wallet.DoesNotExist:
        return Response({'error': 'Wallet not found'}, status=status.HTTP_404_NOT_FOUND)
    
##########################################################################################
#                            req_own_wallet End
##########################################################################################

##########################################################################################
#                            Change Wallet Pin Start
##########################################################################################

@api_view(['POST'])
@permission_classes([AllowAny])
#@permission_classes([HasValidTokenForUser])
def change_wallet_pin(request):
    user_id = request.headers.get('user-id')
    password = request.data.get('password', None)
    old_pin = request.data.get('old_pin', None)
    new_pin = request.data.get('new_pin')

    user = Users.objects.get(user_id=user_id)
    try:
        wallet = Wallet.objects.get(user_id=user)

        #check if wallet is active or not
        if not wallet.is_active:
            if not user.check_password(password):
                return Response({'error': 'Incorrect Password'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if not wallet.check_pin(old_pin):
                return Response({'error': 'Incorrect Old pin'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_pin) != 4 and not new_pin.isdigit():
            return Response({'error': 'Pin must be 4 digits long'}, status=status.HTTP_400_BAD_REQUEST)

        wallet.update_pin(new_pin)
        return Response({'message': 'Pin updated successfully'}, status=status.HTTP_200_OK) 
    except Wallet.DoesNotExist:
        return Response({'error': 'Wallet not found'}, status=status.HTTP_404_NOT_FOUND)
##########################################################################################
#                             Change Wallet Pin End
##########################################################################################


##########################################################################################
#                            req_own_wallet Start
##########################################################################################

@api_view(['POST'])
@permission_classes([AllowAny])
#@permission_classes([HasValidTokenForUser, IsAdmin])
def req_wallet_by_admin(request):
    pass

##########################################################################################
#                            req_own_wallet End
##########################################################################################
##########################################################################################
#                            verify_wallet_pin Start
##########################################################################################
@api_view(['POST'])
@permission_classes([AllowAny])
#@permission_classes([HasValidTokenForUser])
def verify_wallet_pin(request):
    """Verify wallet PIN for authenticated user before transactions"""
    # Get wallet ID and PIN from request
    userid = request.headers.get('user-id')
    pin = request.data.get('pin')
    
    # Validate required fields
    if not pin:
        return Response({
            #'req_access': False,
            'error': 'Enter Pin'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Ensure wallet belongs to authenticated user (security check)
        user = Users.objects.get(user_id=userid)
        wallet = Wallet.objects.get(user_id=user)
        # Verify hashed PIN matches
        if wallet.check_pin(pin):
            return Response({'message': 'PIN verified successfully'}, status=status.HTTP_200_OK)
       
        # PIN verification failed
        return Response({'error': 'Invalid PIN'}, status=status.HTTP_401_UNAUTHORIZED)
    
    except Wallet.DoesNotExist or Users.DoesNotExist:
        # Wallet not found or doesn't belong to user
        return Response({'error': 'Wallet not found'}, status=status.HTTP_404_NOT_FOUND)
##########################################################################################
#                            verify_wallet_pin End
##########################################################################################