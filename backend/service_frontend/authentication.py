# from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from backend.permissions import HasValidTokenForUser
from ..models import Users, Tokens, UserActivity, OTP
# from ..serializers import UsersSerializer
from django.utils import timezone
# from datetime import timedelta
from django.db.models import Q
from backend.utils.validators import validate_nepali_phone
from backend.utils.smallerServiceHandler import get_half_email
from ..utils.otpAndEmailService import send_otp_to_email


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
    
    # Step 3: Set expiration based on user type
    if user.is_admin:
        expiration_days = 1  # Admin tokens valid for 1 day
    else:
        expiration_days = 40  # Farmer/Consumer tokens valid for 40 days
    
    # Step 4: Create the new token using the model's create_token method
    new_token = Tokens.create_token(user, days=expiration_days)
    new_token.device_info = device_info
    new_token.save(update_fields=["device_info"])
    
    return new_token


##########################################################################################
#                            Login Start
##########################################################################################

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
            #'req_access': False,
            'error': 'Credintials is missing.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user_type = 'ADMIN'
        # Search user by userID or Phone and is_admin status
        user = Users.objects.get(Q(user_id=identifier) | Q(phone=identifier), is_admin=is_admin)
        if not is_admin and (user.profile_id.user_type.lower() == 'farmer' or user.profile_id.user_type.lower() == 'verifiedfarmer'):
            user_type = 'Farmer'
        elif not is_admin and (user.profile_id.user_type.lower() == 'consumer' or user.profile_id.user_type.lower() == 'verifiedconsumer'):
            user_type = 'Consumer'
        
        # Verify password
        if not user.check_password(password):
            return Response({
                #'req_access': False,
                'error': 'Credintials is incorrect.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check profile status
        if user.profile_status == 'PENDING':
            return Response({
                'error_code': 'ACCOUNT_PENDING',
                'error': 'Change your password to activate your account.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.profile_status != 'ACTIVATED':
            return Response({
                'error_code': 'ACCOUNT_INACTIVE_OR_SUSPENDED',
                'error': 'Account is inactive or Suspended.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate tokens and manage active tokens
        token_obj = check_generate_save_new_token(user, device_info)
        token = token_obj.token
        refresh_token = token_obj.refresh_token
        
        # Update last activity
        UserActivity.create_activity(user=user, activity="LOGIN", discription="")
        
        # Return response according to documentation
        print('login successful!')
        return Response({
           # 'req_access': True,  # Changed from login_access
            'token': token,
            'refresh_token': refresh_token,
            'user_id': user.user_id,
            'user_type': user_type
            #'error': '
            #"message": 'Login successful!'
        }, status=status.HTTP_200_OK)

        
    except Users.DoesNotExist:
        return Response({
           # 'req_access': False,
            'error': 'User not found!'
        }, status=status.HTTP_404_NOT_FOUND)



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
            #'req_access': False,
            'error': 'Token or user_id is missing. Try to Login through Password.'
        }, status=status.HTTP_406_NOT_ACCEPTABLE)

    try:
        #print('1')
        # Find token entry in database
        token_entry = Tokens.objects.get(
            token=token,
            user_id__user_id=user_id,
            refresh_token=refresh_token,
            device_info=device_info
        )
        
        user = token_entry.user_id
        #print('2')
        # Check profile status
        if user.profile_status != 'ACTIVATED':
            return Response({
               # 'req_access': False,
                'error': 'Account is inactive or Suspended.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if token is expired (after 40 days)
        current_time = timezone.now()
        #print('3')
        if current_time > token_entry.expires_at:
            # Token expired but present - generate new tokens using refresh_token
            new_token_obj = check_generate_save_new_token(user, device_info) 
            new_token = new_token_obj.token
            new_refresh_token = new_token_obj.refresh_token
            
            UserActivity.create_activity(user=user, activity="LOGIN", discription="")
            
            # Return new tokens
            return Response({
                #'req_access': True,
                'token': new_token,
                'refresh_token': new_refresh_token,
                'user_id': user.user_id
            }, status=status.HTTP_200_OK)
        
        else:
            #print('4')
            # Token still valid - just grant access
            UserActivity.create_activity(user=user, activity="LOGIN", discription="")
            
            # According to doc: Second time login returns no new tokens
            return Response({
                #'req_access': True,
                'token' : token,
                'refresh_token': refresh_token,
                'user_id': user.user_id
            }, status=status.HTTP_200_OK)
        
    except Tokens.DoesNotExist:
        #print('5')
        return Response({
            #'req_access': False,
            'error_code': 'Invalid Token. Try to Login through Password.'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_change_password(request):
    user = request.data.get('user_id')
    password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    try:
        user = Users.objects.get(user_id=user, password=password)
        user.set_password(new_password)
        user.save()
    except Users.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
    return Response({"message": "Password changed successfully!"}, status=status.HTTP_200_OK)
    

    
##########################################################################################
#                            Login
##########################################################################################

@api_view(['POST'])
def verify_wallet_pin(request):
    """Verify wallet PIN for authenticated user before transactions"""
    # Get wallet ID and PIN from request
    wallet_id = request.data.get('wallet_id')
    pin = request.data.get('pin')
    
    # Validate required fields
    if not wallet_id or not pin:
        return Response({
            #'req_access': False,
            'error_code': 'MISSING_REQUIRED_FIELDS'
        }, status=status.HTTP_400_BAD_REQUEST)
    
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


##########################################################################################
#                            LogOut
##########################################################################################
@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def logout(request):
    """Logout user by deactivating current token"""
    token = request.headers.get("token")
    
    try:
        token_obj = Tokens.objects.get(token=token)
        token_obj.deactivate()
        return Response({'message': 'Logout successful!'}, status=status.HTTP_200_OK)
    except Tokens.DoesNotExist:
        return Response({'error': 'Invalid Login token.'}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({'error': 'Logout failed:\n' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def logout_all_devices(request):
    """Logout user from all devices by deactivating all tokens"""
    token = request.headers.get("token")
    
    try:
        token_obj = Tokens.objects.get(token=token)
        user = token_obj.user_id
        Tokens.deactivate_all_user_tokens(user)
        return Response({'message': 'Logout from all devices successful!'}, status=status.HTTP_200_OK)
    except Tokens.DoesNotExist:
        return Response({'error': 'Invalid Login token.'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': 'Logout failed:\n' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


##########################################################################################
#                            Logout
##########################################################################################


##########################################################################################
#                            forget Password
##########################################################################################
## request for forget password
@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    identifier = request.data.get("identifier")
    print(identifier)

    # Filter for activated user by user_id or phone
    user_qs = Users.objects.select_related('profile_id').filter(
        Q(user_id=identifier) | Q(phone=identifier),
        profile_status='ACTIVATED'
    )

    if user_qs.exists():
        user = user_qs.first()  # Get the actual user instance
        email = user.get_email_from_userModel()
        user_id = user.user_id
    else:
        print("not found")
        return Response({'error': 'User not found!'}, status=status.HTTP_404_NOT_FOUND)

    print(email)
    print(user_id)
    half_email = get_half_email(email)
    return Response({'half_email': half_email, 'user_id': user_id}, status=status.HTTP_202_ACCEPTED)



## verify Email to send OTP
@api_view(['POST'])
@permission_classes([AllowAny])
def forget_password_verify_email(request):
    user_id = request.data.get('user_id')
    email = request.data.get('email')

    try:
        userObj = Users.objects.select_related('profile_id').get(
            user_id=user_id,
            profile_status='ACTIVATED'
        )
    except Users.DoesNotExist:
        return Response({'error': 'User not found!'}, status=status.HTTP_404_NOT_FOUND)

    if userObj.get_email_from_userModel() != email:
        return Response({'error': 'Invalid email!'}, status=status.HTTP_400_BAD_REQUEST)

    print("1")
    is_emailSent, otp = send_otp_to_email(email)
    if not is_emailSent:
        return Response({'error': 'Email not sent!'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    OTP.create_otp(
        user=userObj,
        otp=otp,
        otp_type='FORGET_PASSWORD',
        created_at=timezone.now(),
        expires_in=2
    )
    print("2")
    return Response({'verification': "True"}, status=status.HTTP_202_ACCEPTED)

## Confirm OTP
@api_view(['POST'])
@permission_classes([AllowAny])
def forget_password_verify_otp(request):
    user_id = request.data.get('user_id')
    otp = request.data.get('otp')

    # Get the latest active OTP for this user
    otp_obj = OTP.objects.filter(
        user_id=user_id,
        otp_type='FORGET_PASSWORD'
    ).order_by('-expires_at').first()

    if not otp_obj:
        return Response({'error': 'No OTP found'}, status=status.HTTP_404_NOT_FOUND)

    # Check effective status
    if otp_obj.effective_status_OTP() != 'ACTIVE':
        return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

    # Compare values
    if otp != otp_obj.get_OTP:
        return Response({'error': 'Invalid OTP!'}, status=status.HTTP_400_BAD_REQUEST)

    # Mark OTP as used
    otp_obj.otp_status = 'USED'
    otp_obj.save(update_fields=['otp_status'])

    return Response({'verified': True}, status=status.HTTP_202_ACCEPTED)



## Reset password
@api_view(['POST'])
@permission_classes([AllowAny])
def forget_password_change_password(request):
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError
    user = request.data.get('user_id')
    password = request.data.get('password')
    try:
        validate_password(password)
    except ValidationError as e:
        return Response({
            'error': ' '.join(e.messages)  # Joins with space
        }, status=status.HTTP_400_BAD_REQUEST)
    user = Users.objects.get(user_id=user, profile_status ='ACTIVATED')
    user.update_password(password)
    UserActivity.create_activity(user, activity="FORGET_PASSWORD", discription="")
    return Response({'message': 'Password changed successfully!'}, status=status.HTTP_200_OK)
    

##########################################################################################
#                            forget Password
##########################################################################################
    


    
    
