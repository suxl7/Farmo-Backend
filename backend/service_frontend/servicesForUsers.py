from rest_framework.decorators import api_view, permission_classes
from backend.permissions import HasValidTokenForUser, IsAdmin
from rest_framework.response import Response
from rest_framework import status
from backend.models import  UsersProfile, Users, Rating, Wallet, Verification
from rest_framework.permissions import  AllowAny
from django.db.models import *


##########################################################################################
#                            other_user_profile Start
##########################################################################################

@api_view(['POST'])
@permission_classes([HasValidTokenForUser, IsAdmin])
#@permission_classes([AllowAny])
def other_user_profile(request):
    """Protected view - requires valid token"""
    userid = request.data.get('user_id')

    user = Users.objects.get(user_id=userid)
    try:
        #profile = UsersProfile.objects.get(profile_id=user.profile_id)
        wallet = Wallet.objects.get(user_id=user)
        return Response({
            'name': user.get_full_name_from_userModel(),
            'user_id': user.user_id,
            'user_type': user.profile_id.user_type,
            'wallet_amount': wallet.amount,
            'phone': user.phone,
            'phone2': user.profile_id.phone02,
            'email': user.profile_id.email,
            'address': user.profile_id.get_Address,
            'dob': user.profile_id.dob,
            'sex': user.profile_id.sex,
            'about': user.profile_id.about,
            'rating': Rating.objects.filter(rated_to=userid).aggregate(Avg('score'))['score__avg'],
            'profile_picture': user.profile_id.profile_url,
            'facebook': user.profile_id.facebook,
            'whatsapp': user.profile_id.whatsapp,
            'join_date': user.profile_id.join_date,
        }, status=status.HTTP_200_OK)
    except UsersProfile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

##########################################################################################
#                            other_user_profile End
##########################################################################################
##########################################################################################
#                            Search User Start 
##########################################################################################
@api_view(['POST'])
#@permission_classes([HasValidTokenForUser, IsAdmin])
@permission_classes([AllowAny])
def search_user(request):
    """Protected view - requires valid token"""
    try:
        search_term = request.data.get('search_data')
        profile_status = request.data.get('profile_status')
        verification = request.data.get('verification')
        user_type = request.data.get('user_type')
        district = request.data.get('district')
        page = request.data.get('page', 1)


        query = Q()

    # Apply filters conditionally
        if search_term:
            query &= Q(user_id__icontains=search_term)

        if profile_status.upper() != 'ALL STATUS':
            query &= Q(profile_status__iexact=profile_status)

        if verification.upper() != 'ALL VERIFICATION':
            # Assuming you have a verification field in Users or UsersProfile
            query &= Q(profile_id__verification__iexact=verification)

        if user_type:
            query &= Q(profile_id__user_type__iexact=user_type)

        if district.upper() != 'ANY DISTRICT':
            # Example: search across multiple address fields
            query &= Q(profile_id__district__icontains=district)

         # Queryset with filters applied
        users_qs = Users.objects.filter(query).order_by("user_id")

    # Pagination logic: 7 per page
        page_size = 7
        start = (page - 1) * page_size
        end = start + page_size
        users = users_qs[start:end]

        user_list = []
        for user in users:
            user_list.append({
                'id': user.user_id,
                'name': user.get_full_name_from_userModel(),
                'contact': user.phone,
                'location': f"{user.profile_id.municipal}, {user.profile_id.district}",
                'rating': Rating.objects.filter(rated_to=user.user_id).aggregate(Avg('score'))['score__avg'] if Rating.objects.filter(rated_to=user.user_id).exists() else 0.0,
            })
        return Response({'users': user_list}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
##########################################################################################
#                            Search USer End
##########################################################################################

##########################################################################################
#                            User Farmer Page
##########################################################################################
@api_view(['POST'])
@permission_classes([AllowAny])
def user_farmer_page(request):
    try:
        farmers = Users.objects.filter(Q(profile_id__user_type='Farmer') | Q(profile_id__user_type='VerifiedFarmer'))
    except Users.DoesNotExist:
        return Response({'error': 'Farmers not found'}, status=status.HTTP_404_NOT_FOUND)
    total_farmer = farmers.count()
    
    activated_farmer = farmers.filter(profile_status='ACTIVATED').count()
    
    verified_farmer = farmers.filter(profile_id__user_type='VerifiedFarmer').count()

    verification_pending_farmer = Verification.objects.filter(
        user_id__in=farmers, status='PENDING'
    ).count()


    return Response({
        'total_farmer': total_farmer,
        'activated_farmer': activated_farmer,
        'verified_farmer': verified_farmer,
        'verification_pending_farmer': verification_pending_farmer,
        }, status=status.HTTP_200_OK)

 
##########################################################################################
#                            User Farmer Page End
##########################################################################################
