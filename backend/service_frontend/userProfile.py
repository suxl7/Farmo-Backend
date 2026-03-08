from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from backend.permissions import HasValidTokenForUser, IsAdmin
from rest_framework.response import Response
from rest_framework import status
from backend.models import Users, UsersProfile, UserActivity, Verification as Ver, Rating, Wallet
from backend.serializers import VerificationSerializer as VS
import secrets
from django.utils import timezone
from django.utils.crypto import get_random_string
from backend.utils.media_handler import FileManager
from backend.utils.validators import (validate_email_format, 
                                      validate_nepali_phone , 
                                      validate_facebook_url, 
                                      validate_whatsapp, 
                                      validate_first_name, 
                                      validate_last_name, 
                                      validate_middle_name, 
                                      validate_password)
from django.core.exceptions import ValidationError
from rest_framework.views import APIView

from backend.utils.whatsapp import normalize_whatsapp

##########################################################################################
#                            Signup Start
##########################################################################################


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register new user with profile"""
    created_by = request.data.get('created_by') # SuperAdmin and Admin or Itself

    user_id = request.data.get('user_id')
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

    print("register")
    print(request.data)
    
    profile_picture =  None

    #join_date = timezone.now()

    from django.utils.dateparse import parse_date
    dob = parse_date(dob_str)
    password = request.data.get('password')
    # Check Password validation
    # if created_by in ['SuperAdmin', 'Admin'] and not user_id:
    #     password = get_random_string(length=8)
    # else:
        
    try:
        validate_password(password)
    except ValidationError as e:
        return Response({
                'error': ''.join(e.messages)  # Joins with space
            }, status=status.HTTP_400_BAD_REQUEST)
        
    

    if not all([user_id, password, f_name, l_name, user_type, phone, province, district, municipal, ward, tole, dob, sex]):
        return Response({
            'error': 'Required fields are missing.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # validation of Name, email, phone, fb, whatsapp
    try:
        validate_first_name(f_name)
        validate_last_name(l_name)
        validate_middle_name(m_name)
        validate_email_format(email)
        validate_nepali_phone(phone)
        if phone02 is not None or phone02 != '':
            validate_nepali_phone(phone02)
        if facebook is not None or facebook != '':
            validate_facebook_url(facebook)
        if whatsapp is not None or whatsapp != '':
            whatsapp = normalize_whatsapp(whatsapp)
            validate_whatsapp(whatsapp)
    except ValidationError as e:
        return Response({
            'error': e.messages  # Joins with space
        }, status=status.HTTP_400_BAD_REQUEST)

    if Users.objects.filter(user_id=user_id).exists():
        return Response({
            #'registration_success': False,
            'error': 'User ID already exists.'}, status=status.HTTP_400_BAD_REQUEST)
    

    if user_type == 'SuperAdmin' and not created_by == 'SuperAdmin':
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
    
    
    result = save_profile_file(user_id, profile_picture)

    if profile_picture and not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    profile_picture_url = result['file_url'] if profile_picture else None

    # if created_by in ['Admin', 'SuperAdmin']:
        # UserActivity.create_activity(user=user, activity="SIGNUP", discription="By Admin.")
    
    profile = UsersProfile.create_profile(
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
    # print(3)
    # print(profile.profile_id)
    # print(4)
    if created_by in ['Admin', 'SuperAdmin']:
        profile_status = 'PENDING'
    else:
        profile_status = 'ACTIVATED'
    
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
'''
This is for the users to send verification request.
'''
@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def verification_request(request):
    user_id = request.headers.get('user-id')
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
    Ver.objects.create()

    return Response({
        'message': 'Verification request submitted successfully.'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([HasValidTokenForUser, IsAdmin])
def verification_response(request):
    v_user = request.data.get("user_id")
    ver_obj = Ver.objects.get(user_id = v_user)
    


# class get_Verification(APIView):
#     permission_classes = [HasValidTokenForUser, IsAdmin]
#     def post(self, request):
#         serializer = Ver(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

##########################################################################################
#                            verification
##########################################################################################
##########################################################################################
#                            Payment Method 
##########################################################################################


@api_view(['PUT'])
@permission_classes([HasValidTokenForUser])
def update_payment_method(request):
    user_id = request.headers.get('user-id')
    payment_methods = request.data.get('payment_methods')  # expects a list

    if not user_id or not payment_methods:
        return Response({
            'error': 'user_id and payment_methods are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(payment_methods, list):
        return Response({
            'error': 'payment_methods must be a list'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        profile = UsersProfile.objects.get(profile_id=user_id)
        # overwrite with the new list
        profile.payment_method = payment_methods
        profile.save(update_fields=['payment_method'])

        return Response({
            'message': 'Payment methods saved successfully',
            'data': {
                'profile_id': profile.profile_id,
                'payment_methods': profile.payment_method
            }
        }, status=status.HTTP_200_OK)

    except UsersProfile.DoesNotExist:
        return Response({
            'error': 'User profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

    
'''
This methods is for get all available payment methods of farmer.
Like: Cash on Delivery, System Wallet, External Wallet like khalti, esewa, etc.
'''
@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def get_payment_method(request):
    user_id = request.headers.get('user-id')  # safer: headers not header
    if not user_id:
        return Response({
            'error': 'user_id is required in headers'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment_method = Users.objects.get(user_id=user_id).profile_id.payment_method
       
        return Response({
            'message': 'Payment methods retrieved successfully',
            'data': payment_method  # this will be a list like ["Wallet", "QR", "CashOnDelivery"]
        }, status=status.HTTP_200_OK)

    except UsersProfile.DoesNotExist:
        return Response({
            'error': 'User profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


##########################################################################################
#                            Payment Methods End
##########################################################################################


##########################################################################################
#                            Change Password
##########################################################################################

@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def change_password(request):
    userid = request.headers.get('user-id')
    old_password = request.data.get('current_password')
    new_password = request.data.get('new_password')

    user = Users.objects.get(user_id=userid, profile_status ='ACTIVATED')
    if not user.check_password(old_password):
        return Response({'error': 'Incorrect old password!'}, status=status.HTTP_400_BAD_REQUEST)
 
    userAct = UserActivity.objects.filter(user_id=user, activity="CHANGE_PASSWORD").order_by('-timestamp').first()
    date_diff = timezone.now() - userAct.timestamp
    if date_diff.days < 5:
        return Response ({'error': "Last Change password was less than 5 days ago."}, status=status.HTTP_400_BAD_REQUEST)

    user.update_password(new_password)
    user.save()
    UserActivity.create_activity(user, activity="CHANGE_PASSWORD", discription="")
    
    return Response({}, status=status.HTTP_200_OK)
    
##########################################################################################
#                            Change Password End
##########################################################################################

##########################################################################################
#                            Update Profile Picture
##########################################################################################

@api_view(['POST'])
@permission_classes([AllowAny])
def update_profile_picture(request):
    user_id = request.headers.get('user-id')
    new_picture = request.FILES.get('profile_picture')

    # Call helper method to save file
    result = save_profile_file(user_id, new_picture)

    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    # Update database here
    user_obj = Users.objects.get(user_id=user_id)
    profile = UsersProfile.objects.get(profile_id=user_obj.profile_id.profile_id)
    profile.profile_url = result['file_url']
    profile.save()

    # Log activity
    UserActivity.create_activity(user_obj, activity="UPDATE_PROFILE_PIC", discription="")

    return Response({'message': 'Profile picture updated successfully.'}, status=status.HTTP_200_OK)


def save_profile_file(user_id, new_picture):
    # Initialize FileManager
    file_manager = FileManager(user_id)

    # Save new picture (will replace old one)
    result = file_manager.save_profile_file(
        file=new_picture,
        file_purpose='profile-pic',
        max_size_mb=5
    )
    return result


##########################################################################################
#                            Profile Picture Update End
##########################################################################################

##########################################################################################
#                            View Profile picture Start
##########################################################################################
import base64
import mimetypes
from django.conf import settings
from django.db.models import Avg

def get_user_profile_data(user):
    """
    Helper method to get user profile data with encoded profile picture
    
    Args:
        user: Users model instance
        
    Returns:
        dict: Dictionary containing user profile data and base64 encoded image
    """
    profile = user.profile_id
    join_date = profile.join_date.strftime('%Y-%m-%d')
    url = str(profile.profile_url)
    url = url.replace(
    f"Uploaded_Files/{user.user_id}/profile/profile-pic-",
    "")



    return {
        'user_id': user.user_id,
        'full_name': profile.get_Full_Name,
        'address': profile.get_Address,
        'phone': user.phone,
        'phone2': profile.phone02,
        'user_type': profile.user_type,
        'email': profile.email,
        'facebook': profile.facebook,
        'whatsapp': profile.whatsapp,
        'join_date': join_date,
        'about': profile.about,
        'dob': profile.dob,
        'sex': profile.sex,
        'profile_picture': url,
    }


@api_view(['POST'])
@permission_classes([AllowAny])
#@permission_classes([HasValidTokenForUser])
def view_own_profile(request):
    """View own profile - accessible by any authenticated user"""
    userid = request.headers.get('user-id')
    
    try:
        user = Users.objects.get(user_id=userid)
        profile_data = get_user_profile_data(user)
        #print(userid)
        return Response(profile_data, status=status.HTTP_200_OK)
            
    except Users.DoesNotExist:
        #print("userid")
        return Response({
            'error': 'User not found.'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
#@permission_classes([HasValidTokenForUser, IsAdmin])
@permission_classes([AllowAny])
def view_user_profile_by_admin(request):
    """View any user's profile - admin only"""
    userid = request.data.get('target_user_id')  
    
    if not userid:
        return Response({
            'error': 'user_id parameter is required.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = Users.objects.get(user_id=userid)
        profile_data = get_user_profile_data(user)

        rating = Rating.objects.filter(rated_to=userid).aggregate(avg_score=Avg('score'))['avg_score']
        if rating is None:
            rating = 0.0
        else:
            rating = round(rating, 1)

        profile_data['rating'] = rating
        wallet_balance = Wallet.objects.get(user_id=user).balance
        profile_data['wallet_balance'] = wallet_balance
        return Response(profile_data, status=status.HTTP_200_OK)
            

    except Users.DoesNotExist:
        return Response({
            'error': 'User not found.'
        }, status=status.HTTP_404_NOT_FOUND)
    except Rating.DoesNotExist:
        return Response({
            'error': 'Rating not found.'
        }, status=status.HTTP_404_NOT_FOUND)


##########################################################################################
#                            View Profile Picture End
##########################################################################################
##########################################################################################
#                            Update own Profile Details Start
##########################################################################################
@api_view(['POST'])
@permission_classes([AllowAny])
def update_profile(request):
    from backend.utils.whatsapp import normalize_whatsapp

    userid = request.headers.get('user-id')
    data = request.data
    f_name = data.get("f_name")
    m_name = data.get("m_name")
    l_name = data.get("l_name")
    phone = data.get("phone")
    phone2 = data.get("phone2")
    facebook = data.get("facebook")
    whatsapp = data.get("whatsapp")
    province = data.get("province")
    district = data.get("district")
    municipal = data.get("municipal")
    ward = data.get("ward")
    tole = data.get("tole")
    about = data.get("about")
    dob = data.get("dob")
    sex = data.get("sex")

    if not f_name or not l_name or not phone or not province or not district or not municipal or not ward or not tole or not dob or not sex:
        return Response({"error": "Required fields are missing."}, status=status.HTTP_400_BAD_REQUEST)


    try:
        user = Users.objects.get(user_id=userid)
        profile = UsersProfile.objects.get(profile_id=user.profile_id.profile_id)
        profile.f_name = f_name
        profile.m_name = m_name
        profile.l_name = l_name
        profile.phone02 = phone2
        profile.facebook = facebook
        profile.whatsapp = normalize_whatsapp(whatsapp) if whatsapp else None
        profile.province = province
        profile.district = district
        profile.municipal = municipal
        profile.ward = ward
        profile.tole = tole
        profile.about = about
        profile.dob = dob
        profile.sex = sex
        profile.save()
        user.phone = phone
        user.save()

        return Response({},status= status.HTTP_200_OK)
    except Users.DoesNotExist:
        return Response({
            'error': 'User not found.' }, status=status.HTTP_404_NOT_FOUND)
    except UsersProfile.DoesNotExist:
        return Response({
            'error': 'Profile not found.' }, status=status.HTTP_404_NOT_FOUND)
    

@api_view(['POST'])
@permission_classes([AllowAny])
def update_user_profile(request):
    from backend.utils.whatsapp import normalize_whatsapp

    userid = request.data.get('user_id')
    data = request.data
    f_name = data.get("f_name")
    m_name = data.get("m_name")
    l_name = data.get("l_name")
    phone = data.get("phone")
    phone2 = data.get("phone2")
    facebook = data.get("facebook")
    whatsapp = data.get("whatsapp")
    province = data.get("province")
    district = data.get("district")
    municipal = data.get("municipal")
    ward = data.get("ward")
    tole = data.get("tole")
    about = data.get("about")
    dob = data.get("dob")
    sex = data.get("sex")

    if not f_name or not l_name or not phone or not province or not district or not municipal or not ward or not tole or not dob or not sex:
        return Response({"error": "Required fields are missing."}, status=status.HTTP_400_BAD_REQUEST)


    try:
        user = Users.objects.get(user_id=userid)
        profile = UsersProfile.objects.get(profile_id=user.profile_id.profile_id)
        profile.f_name = f_name
        profile.m_name = m_name
        profile.l_name = l_name
        profile.phone02 = phone2
        profile.facebook = facebook
        profile.whatsapp = normalize_whatsapp(whatsapp) if whatsapp else None
        profile.province = province
        profile.district = district
        profile.municipal = municipal
        profile.ward = ward
        profile.tole = tole
        profile.about = about
        profile.dob = dob
        profile.sex = sex
        profile.save()
        user.phone = phone
        user.save()

        return Response({},status= status.HTTP_200_OK)
    except Users.DoesNotExist:
        return Response({
            'error': 'User not found.' }, status=status.HTTP_404_NOT_FOUND)
    except UsersProfile.DoesNotExist:
        return Response({
            'error': 'Profile not found.' }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def check_password(request):
    userid = request.headers.get('user-id')
    password = request.data.get('password')
    try:
        user = Users.objects.get(user_id=userid)
        if user.check_password(password):
            return Response({}, status=status.HTTP_200_OK)
        else:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
    except Users.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

##########################################################################################
#                            Update own Profile Details End
##########################################################################################
