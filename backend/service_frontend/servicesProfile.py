from rest_framework.decorators import api_view, permission_classes
from backend.permissions import HasValidTokenForUser
from rest_framework.response import Response
from rest_framework import status
from backend.models import  UsersProfile, Users, Rating
from rest_framework.permissions import  AllowAny


@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def view_profile(request):
    """Protected view - requires valid token"""
    user = request.headers.get('userid')
    user = Users.objects.get(user_id=user)
    try:
        profile = UsersProfile.objects.get(profile_id=user.profile_id)
        return Response({
            'user_id': user.user_id,
            'phone': user.phone,
            'profile': {
                'name': f"{profile.f_name} {profile.l_name}",
                'email': profile.email,
                'join_date': profile.join_date
            }
        }, status=status.HTTP_200_OK)
    except UsersProfile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

