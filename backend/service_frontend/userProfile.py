from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from backend.permissions import HasValidTokenForUser
from rest_framework.response import Response
from rest_framework import status
from backend.models import Users, UsersProfile, UserActivity, PaymentMethodAccepts
import secrets
from django.utils import timezone
from django.utils.crypto import get_random_string
from backend.utils.media_handler import FileManager
from backend.utils.dataVerifier import is_email, is_phone



##########################################################################################
#                            Signup Start
##########################################################################################


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register new user with profile"""
    created_by = request.data.get('created_by')

    user_id = request.data.get('user_id')
    if created_by == 'Admin':
        password = get_random_string(length=8)
    else:
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
    email = request.data.get('email')
    whatsapp = request.data.get('whatsapp', None)
    facebook = request.data.get('facebook', None)
    about = request.data.get('about', None)
    sex = request.data.get('sex')
    dob_str = request.data.get('dob')
    
    user_type = request.data.get('user_type')
    
    profile_picture = request.FILES.get('profile_picture', None)

    join_date = timezone.now()

    from django.utils.dateparse import parse_date
    dob = parse_date(dob_str)

    if not all([user_id, password, f_name, l_name, user_type, phone, province, district, municipal, ward, tole, dob, sex]):
        return Response({
            'error': 'Required fields are missing.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    if Users.objects.filter(user_id=user_id).exists():
        return Response({
            #'registration_success': False,
            'error': 'User ID already exists.'}, status=status.HTTP_400_BAD_REQUEST)
    
    #check given name phone no and email are valid or not.
    if not is_phone(phone):
        return Response({
            'error': 'Invalid phone number.'}, status=status.HTTP_400_BAD_REQUEST)
    if phone02 and not is_phone(phone02):
        return Response({
            'error': 'Invalid secondary phone number.'}, status=status.HTTP_400_BAD_REQUEST)
    if not is_email(email):
        return Response({
            'error': 'Invalid email.'}, status=status.HTTP_400_BAD_REQUEST)
    

    if user_type == 'SuperAdmin' and created_by == 'Admin':
        return Response({
            'error': 'You are trying to create higher level user.'}, status=status.HTTP_403_FORBIDDEN)
    
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
            'error': 'You have already created 3 accounts with this phone number. Try another phone number.'}, status=status.HTTP_400_BAD_REQUEST)

    active_user_count = Users.objects.filter(phone=phone, profile_status__in=['ACTIVE', 'PENDING']).count()
    if active_user_count >= 1:
        return Response({
           # 'registration_success': False,
            'error': 'You have already created an account with this phone number.'}, status=status.HTTP_400_BAD_REQUEST)
    
    
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
                'error': 'Profile picture upload failed.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        profile_picture_url = result['file_url']
    
    profile = UsersProfile.objects.create_profile(
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
        email=email,
        facebook=facebook or None,
        whatsapp=whatsapp or None,
        about=about or None,
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
    if created_by in ['Admin', 'SuperAdmin']:
        message = "Registration successful. Use password: \"" + password + "\" to login." if profile_status == 'PENDING' else "Registration successful. Please login."
    else:
        message = "Registration successful. Please login."
    
    return Response({
       'message': message
    }, status=status.HTTP_201_CREATED)

##########################################################################################
#                            Signup
##########################################################################################
##########################################################################################
#                            Verification Start
##########################################################################################

@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
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
            'error': selfie_result['error']
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # TODO: Save to Verification model
    
    return Response({
        'message': 'Verification request submitted successfully.'
    }, status=status.HTTP_200_OK)

##########################################################################################
#                            verification
##########################################################################################


##########################################################################################
#                            Update Profile Picture
##########################################################################################

@api_view(['PUT'])
@permission_classes([HasValidTokenForUser])
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
            'error': result['error']
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Update database
    profile = UsersProfile.objects.get(user_id=user_id)
    profile.profile_url = result['file_url']
    profile.save()
    
    UserActivity.create_activity(request.user, activity="UPDATE_PROFILE_PIC", discription="")

    return Response({
        'message': 'Profile picture updated successfully.'
    }, status=status.HTTP_200_OK)

##########################################################################################
#                            Profile Picture Update End
##########################################################################################
##########################################################################################
#                            Payment Method 
##########################################################################################


@api_view(['PUT'])
@permission_classes([HasValidTokenForUser])
def add_payment_method(request):
    # safer way: request.headers not request.header
    user_id = request.headers.get('user_id')
    payment_method = request.data.get('payment_method')

    if not user_id or not payment_method:
        return Response({
            'error': 'user_id and payment_method are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # create or update payment method record
        pm_obj, created = PaymentMethodAccepts.objects.update_or_create(
            pm_id=f"{user_id}-payment-method",
            defaults={
                "user_id": user_id,
                "payment_method": payment_method
            }
        )

        return Response({
            'message': 'Payment method saved successfully',
            'data': {
                'pm_id': pm_obj.pm_id,
                'created': created
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def get_payment_method(request):
    user_id = request.headers.get('user_id')
    if not user_id:
        return Response({
            'error': 'user_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        pm_obj = PaymentMethodAccepts.objects.get(user_id=user_id)
        pm_obj.get_payment_methods()
        return Response({
            'pm_id': pm_obj.pm_id,
            'payment_method': pm_obj.get_payment_methods()  
        }, status=status.HTTP_200_OK)
    
    except PaymentMethodAccepts.DoesNotExist:
        return Response({
            'error': 'Payment method not found'
        }, status=status.HTTP_404_NOT_FOUND)

##########################################################################################
#                            Payment Methods End
##########################################################################################
