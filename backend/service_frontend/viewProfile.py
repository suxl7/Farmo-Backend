from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from backend.models import Users, UsersProfile
from backend.serializers import UsersSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """Protected view - requires valid token"""
    user = request.user
    try:
        profile = UsersProfile.objects.get(profile_id=user.profile_id)
        return Response({
            'user_id': user.user_id,
            'phone': user.phone,
            'is_admin': user.is_admin,
            'profile': {
                'name': f"{profile.f_name} {profile.l_name}",
                'email': profile.email,
                'join_date': profile.join_date
            }
        }, status=status.HTTP_200_OK)
    except UsersProfile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_example(request):
    """Example protected endpoint"""
    return Response({
        'message': 'This is a protected endpoint',
        'user_id': request.user.user_id
    }, status=status.HTTP_200_OK)
