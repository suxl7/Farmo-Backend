from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from backend.serializers import UsersSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from backend.models import Users, UsersProfile
import secrets
import os
from django.conf import settings
from backend.utils.update_last_activity import get_online_status

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
@permission_classes([AllowAny])
def register(request):
    """Register new user with profile"""
    user_id = request.data.get('user_id')
    password = request.data.get('password')
    f_name = request.data.get('f_name')
    m_name = request.data.get('m_name')
    l_name = request.data.get('l_name')
    province = request.data.get('province')
    district = request.data.get('district')
    ward = request.data.get('ward')
    tole = request.data.get('tole')
    phone = request.data.get('phone')
    phone02 = request.data.get('phone2')
    email = request.data.get('email')
    whatsapp = request.data.get('whatsapp')
    facebook = request.data.get('facebook')
    about = request.data.get('about')
    sex = request.data.get('sex')
    dob = request.data.get('dob')
    user_type = request.data.get('user_type')
    created_by = request.data.get('created_by')
    profile_picture = request.FILES.get('profile_picture')

    if user_type.lower() != "admin":
        is_admin = False
    else:
        is_admin = True
        user_type = None
    
    if not all([user_id, password, f_name, l_name, user_type]):
        return Response({'error': 'Required fields: user_id, password, f_name, l_name, user_type'}, status=status.HTTP_400_BAD_REQUEST)
    
    if Users.objects.filter(user_id=user_id).exists():
        return Response({'error': 'User ID already exists'}, status=status.HTTP_400_BAD_REQUEST)
    
    profile_id = f"P{secrets.token_hex(8).upper()}"
    profile_picture_url = None
    
    if profile_picture:
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'profiles')
        os.makedirs(upload_dir, exist_ok=True)
        file_ext = os.path.splitext(profile_picture.name)[1]
        file_name = f"{profile_id}{file_ext}"
        file_path = os.path.join(upload_dir, file_name)
        
        with open(file_path, 'wb+') as destination:
            for chunk in profile_picture.chunks():
                destination.write(chunk)
        
        profile_picture_url = f"{settings.MEDIA_URL}profiles/{file_name}"
    
    profile = UsersProfile.objects.create(
        profile_id=profile_id,
        profile_url=profile_picture_url or None,
        f_name=f_name,
        m_name=m_name or None,
        l_name=l_name,
        user_type=user_type,
        province=province,
        district=district,
        ward=ward,
        tole=tole or None,
        dob=dob,
        sex=sex,
        phone02=phone02 or None,
        email=email or None,
        facebook=facebook or None,
        whatsapp=whatsapp or None,
        about=about or None
    )
    
    profile_status = 'PENDING' if created_by else 'ACTIVATED'
    
    user = Users.objects.create(
        user_id=user_id,
        phone=phone,
        profile_status=profile_status,
        profile_id=profile,
        is_admin=is_admin
    )
    user.set_password(password)
    user.save()
    
    return Response({
        'message': 'User registered successfully',
        'is_user_registered': True
    }, status=status.HTTP_201_CREATED)

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

