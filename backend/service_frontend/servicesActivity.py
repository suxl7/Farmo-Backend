from django.utils import timezone
from datetime import timedelta
from backend.models import UserActivity
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from backend.permissions import ConnectionOnly
from rest_framework.response import Response
from backend.models import Users


@api_view(['GET'])
@permission_classes([AllowAny])
def check_userid(request):
    """Check if userID is available during registration"""
    user_id = request.GET.get('user_id')
    if not user_id:
        return Response({'status': 1}, status=400)
    
    """Check existence of user_id in Users model [exists is boolean]"""
    exists = Users.objects.filter(user_id=user_id).exists()
    return Response({'status': 1 if exists else 0})    
    

@api_view(['POST'])
@permission_classes([IsAuthenticated, ConnectionOnly])
def get_online_status(request):
    """Get online status of a connected user"""
    try:
        target_user=request.data.get('target_user')
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
