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


@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
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

    return Response({"status": status})


@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def get_address(request):
    """Get the address for an order"""
    user = request.headers.get('userid')
    address_of = request.data.get('address_of')
    user_id = request.data.get('userid') if request.data.get('userid') else None

    try:
        if address_of.lower() == 'consumer':
            address = UsersProfile.objects.get(user_id=user).get_Address()
        elif address_of.lower() in  ['farmer', 'seller', 'admin']:
            address = UsersProfile.objects.get(user_id=user_id).get_Address()
        

        return Response({'address': address}, status=status.HTTP_200_OK)
    
    except ObjectDoesNotExist:
        return Response({'error': 'User not found!'}, status=status.HTTP_404_NOT_FOUND)
