from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from backend.models import UserActivity, UsersProfile
from rest_framework.decorators import api_view, permission_classes
from backend.permissions import ConnectionOnly
from rest_framework.response import Response
from backend.models import Users
from backend.permissions import HasValidTokenForUser
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import AllowAny

@api_view(['POST'])
@permission_classes([AllowAny])
def change_to_farmer(request):
    user_id = request.headers.get('user-id')
    user = Users.objects.get(user_id=user_id)
    password = request.data.get('password')
    if not user.check_password(password):
        return Response({'error': 'Incorrect password'}, status=status.HTTP_400_BAD_REQUEST)
    
    if user.profile_id.user_type != 'Consumer':
        user.profile_id.user_type = 'Farmer'
    elif user.profile_id.user_type != 'VerifiedConsumer':
        user.profile_id.user_type = 'VerifiedFarmer'
    else:
        return Response({'error': 'Invalid user type'}, status=status.HTTP_400_BAD_REQUEST)
    
    user.profile_id.save()
    return Response({'message': 'User type changed successfully'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def check_userid_available(request):
    """Check if userID is available"""
    user_id = request.data.get('user_id')
  
    if not user_id:
        return Response({'status': 1}, status=status.HTTP_200_OK)
    
    """Check existence of user_id in Users model [exists is boolean]"""
    exists = Users.objects.filter(user_id=user_id).exists()
    return Response({'status': 1 if exists else 0}, status=status.HTTP_200_OK)    

@api_view(['POST'])
@permission_classes([HasValidTokenForUser, ConnectionOnly])
def get_online_status(request):
    """Get online status of a connected user"""
    try:
        target_user=request.data.get('target_user')
        # Why use request.META? Because request.headers is case-insensitive and may not work in all environments
        # Why use 'HTTP_AUTHORIZATION'? Because Django prepends 'HTTP_' to header names in request.META
        # Why use this whole line? To extract the token from the 'Authorization: Bearer <token>' format

        activity = UserActivity.objects.filter(user_id=target_user).order_by('-timestamp').first() # get latest activity
        last_activity = activity.timestamp

        diff = timezone.now() - last_activity

        if diff < timedelta(minutes=5):
            status = "online"
        elif diff < timedelta(minutes=35):
            minutes_ago = int(diff.total_seconds() / 60)
            status = f"active {minutes_ago} minutes ago"
        else:
            status = "offline"

    except (Users.DoesNotExist, UserActivity.DoesNotExist):
        status = "offline"

    return Response({"status": status}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def get_address(request):
    """Get the address for an order"""
    userid = request.data.get('user_id')
    response = address(userid)
    return response
    
@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def get_own_address(request):
    """Get the address for an order"""
    userid = request.headers.get('user-id')
    response = address(userid)
    return response

def address(userid):
    try:
        user = Users.objects.get(user_id=userid).profile_id
        
        province = user.province
        district = user.district
        municipal = user.municipal
        ward = user.ward
        tole = user.tole
        

        return Response({'province': province, 'district': district, 'municipal': municipal, 'ward': ward, 'tole': tole}, status=status.HTTP_200_OK)
    
    except ObjectDoesNotExist:
        return Response({'error': 'User not found!'}, status=status.HTTP_404_NOT_FOUND)
