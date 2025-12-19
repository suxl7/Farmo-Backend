from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from backend.models import Users
from backend.utils.update_last_activity import get_online_status


@api_view(['GET'])
@permission_classes([AllowAny])
def user_online_status(request):
    """Get user online status"""
    user_id = request.GET.get('user_id')
    
    if not user_id:
        return Response({'error': 'user_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = Users.objects.get(user_id=user_id)
        online_status = get_online_status(user)
        return Response({'user_id': user_id, 'status': online_status})
    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
