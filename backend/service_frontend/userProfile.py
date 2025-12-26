from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from backend.serializers import UsersSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from backend.models import Users, UsersProfile, UserActivity
import secrets
from django.utils import timezone
import os
from django.conf import settings
#from backend.service_frontend.servicesActivity import get_online_status
from backend.utils.file_manager import FileManager
@api_view(['GET'])
@permission_classes([AllowAny])
def check_userid(request):
    """Check if userID is available during registration"""
    user_id = request.GET.get('user_id')
    if not user_id:
        return Response({'status': 1}, status=status.HTTP_400_BAD_REQUEST)
    
    """Check existence of user_id in Users model [exists is boolean]"""
    exists = Users.objects.filter(user_id=user_id).exists()
    return Response({'status': 1 if exists else 0})


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register new user with profile"""
    user_id = request.data.get('user_id')
    password = request.data.get('password')
    f_name = request.data.get('f_name') # required
    m_name = request.data.get('m_name', None) # optional
    l_name = request.data.get('l_name')
    province = request.data.get('province')
    district = request.data.get('district')
    municipal = request.data.get('municipal')
    ward = request.data.get('ward')
    tole = request.data.get('tole')
    phone = request.data.get('phone')
    phone02 = request.data.get('phone2', None)
    email = request.data.get('email', None)
    whatsapp = request.data.get('whatsapp', None)
    facebook = request.data.get('facebook', None)
    about = request.data.get('about', None)
    sex = request.data.get('sex')
    dob = request.data.get('dob')
    user_type = request.data.get('user_type')
    created_by = request.data.get('created_by')
    profile_picture = request.FILES.get('profile_picture', None)

    join_date = timezone.now()


    if not all([user_id, password, f_name, l_name, user_type, phone, province, district, municipal, ward, tole, dob, sex]):
        return Response({
            'registration_success': False,
            'error_code': 'MISSING_REQUIRED_FIELDS'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    if Users.objects.filter(user_id=user_id).exists():
        return Response({
            'registration_success': False,
            'error_code': 'USERID_EXISTS'}, status=status.HTTP_400_BAD_REQUEST)
    
    if user_type == 'SuperAdmin' and created_by == 'Admin':
        return Response({
            'registration_success': False,
            'error_code': 'INSUFFICIENT_PRIVILEGES'}, status=status.HTTP_403_FORBIDDEN)
    
    if user_type not in ['SuperAdmin', 'Admin']:
        is_admin = False
    else:
        is_admin = True

    '''
    A user can able to create total 3 accounts with one phone number but must have 1 active account at a time.
    Check if phone number already exists ACTIVE or PENDING status in Users model. If exists, return error.
    '''
    if Users.objects.filter(phone=phone).count() >= 3:
        return Response({
            'registration_success': False,
            'error_code': 'PHONE_NUMBER_ACCOUNT_LIMIT_REACHED'}, status=status.HTTP_400_BAD_REQUEST)

    active_user_count = Users.objects.filter(phone=phone, profile_status__in=['ACTIVE', 'PENDING']).count()
    if active_user_count >= 1:
        return Response({
            'registration_success': False,
            'error_code': 'PHONE_EXISTS_ACTIVE_ACCOUNT'}, status=status.HTTP_400_BAD_REQUEST)
    
    profile_id = f"P{secrets.token_hex(8).upper()}"
    
    file_manager = FileManager(user_id)
    
    profile_picture_url = None
    if profile_picture:
        result = file_manager.save_profile_file(
            file=profile_picture,
            file_purpose='profile-pic',
            max_size_mb=5
        )
        
        if not result['success']:
            return Response({
                'registration_success': False,
                'error_code': 'PROFILE_PICTURE_UPLOAD_FAILED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        profile_picture_url = result['file_url']
    
    profile = UsersProfile.objects.create(
        profile_id=profile_id,
        profile_url=profile_picture_url or None,
        f_name=f_name,
        m_name=m_name or None,
        l_name=l_name,
        user_type=user_type,
        province=province,
        district=district,
        municipal=municipal,
        ward=ward,
        tole=tole,
        dob=dob,
        sex=sex,
        phone02=phone02 or None,
        email=email or None,
        facebook=facebook or None,
        whatsapp=whatsapp or None,
        about=about or None,
        join_date=join_date
    )

    if created_by in ['Admin', 'SuperAdmin']:
        profile_status = 'PENDING'
    else:
        profile_status = 'ACTIVE'
    
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
        'registration_success': True
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verification_request(request):
    user_id = request.data.get('user_id')
    id_front = request.FILES.get('id_front')
    id_back = request.FILES.get('id_back')
    selfie_with_id = request.FILES.get('selfie_with_id')
    
    # Initialize FileManager
    file_manager = FileManager(user_id)
    
    # Save front document
    front_result = file_manager.save_profile_file(
        file=id_front,
        file_purpose='verification-doc-front',
        allowed_extensions=['.jpg', '.jpeg', '.png', '.pdf'],
        max_size_mb=5
    )
    
    if not front_result['success']:
        return Response({
            'verification_success': False,
            'error': front_result['error']
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Save back document
    back_result = file_manager.save_profile_file(
        file=id_back,
        file_purpose='verification-doc-back',
        allowed_extensions=['.jpg', '.jpeg', '.png', '.pdf'],
        max_size_mb=5
    )
    
    if not back_result['success']:
        # Clean up front file
        file_manager.delete_file('profile', front_result['file_name'])
        return Response({
            'verification_success': False,
            'error': back_result['error']
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Save selfie
    selfie_result = file_manager.save_profile_file(
        file=selfie_with_id,
        file_purpose='selfie-with-id',
        max_size_mb=5
    )
    
    if not selfie_result['success']:
        file_manager.delete_file('profile', front_result['file_name'])
        file_manager.delete_file('profile', back_result['file_name'])
        return Response({
            'verification_success': False,
            'error': selfie_result['error']
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # TODO: Save to Verification model
    
    return Response({
        'verification_success': True,
        'verification_id': f"V{secrets.token_hex(8).upper()}",
        'documents': {
            'front': front_result['file_url'],
            'back': back_result['file_url'],
            'selfie': selfie_result['file_url']
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile_picture(request):
    user_id = request.user.user_id
    new_picture = request.FILES.get('profile_picture')
    
    # Initialize FileManager
    file_manager = FileManager(user_id)
    
    # Save new picture (will replace old one)
    result = file_manager.save_profile_file(
        file=new_picture,
        file_purpose='profile-pic',
        max_size_mb=5
    )
    
    if not result['success']:
        return Response({
            'success': False,
            'error': result['error']
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Update database
    profile = UsersProfile.objects.get(user_id=user_id)
    profile.profile_url = result['file_url']
    profile.save()
    
    UserActivity.create_activity(request.user, activity="UPDATE_PROFILE_PIC", discription="")

    return Response({
        'success': True,
        'profile_picture_url': result['file_url']
    }, status=status.HTTP_200_OK)