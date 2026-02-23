from rest_framework.decorators import api_view, permission_classes
from backend.permissions import HasValidTokenForUser, IsAdmin
from rest_framework.response import Response
from rest_framework import status
from backend.models import  UsersProfile, Users, Rating, Wallet, Verification, Transaction
from rest_framework.permissions import  AllowAny
from django.db.models import *


##########################################################################################
#                            other_user_profile Start
##########################################################################################

@api_view(['POST'])
#@permission_classes([HasValidTokenForUser, IsAdmin])
@permission_classes([AllowAny])
def other_user_profile(request):
    """Protected view - requires valid token"""
    userid = request.data.get('user_id')

    
    try:
        user = Users.objects.get(user_id=userid)
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
    except Users.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

##########################################################################################
#                            other_user_profile End
##########################################################################################
##########################################################################################
#                            Search User Start 
##########################################################################################
@api_view(['POST'])
@permission_classes([HasValidTokenForUser, IsAdmin])
def search_user(request):
    """Protected view - requires valid token"""
    try:
        search_term    = request.data.get('search_data', '').strip()
        profile_status = request.data.get('profile_status', '')
        verification   = request.data.get('verification', '')
        user_type      = request.data.get('user_type', '')
        district       = request.data.get('district', '')
        page           = request.data.get('page', 1)

        query = Q()

        # ── Search term ───────────────────────────────────────────────────────
        # BUG FIX: original condition `!= '' or != None` is always True.
        # Correct guard: only filter when the term is a non-empty string.
        if search_term:
            query &= (
                Q(user_id__icontains=search_term)
                | Q(profile_id__f_name__icontains=search_term)
                | Q(profile_id__m_name__icontains=search_term)
                | Q(profile_id__l_name__icontains=search_term)
            )

        # ── Profile status ────────────────────────────────────────────────────
        if profile_status and profile_status.upper() != 'ALL STATUS':
            query &= Q(profile_status__iexact=profile_status)

        # ── Verification ──────────────────────────────────────────────────────
        if verification and verification.upper() != 'ALL VERIFICATION':
            query &= Q(profile_id__verification__iexact=verification)

        # ── User type ─────────────────────────────────────────────────────────
        if user_type:
            ut = user_type.lower()
            if ut in ['farmer', 'verifiedfarmer']:
                query &= (
                    Q(profile_id__user_type__iexact='Farmer')
                    | Q(profile_id__user_type__iexact='VerifiedFarmer')
                )
            elif ut in ['consumer', 'verifiedconsumer']:
                query &= (
                    Q(profile_id__user_type__iexact='Consumer')
                    | Q(profile_id__user_type__iexact='VerifiedConsumer')
                )

        # ── District ──────────────────────────────────────────────────────────
        if district and district.upper() != 'ANY DISTRICT':
            query &= Q(profile_id__district__icontains=district)

        # ── Queryset ──────────────────────────────────────────────────────────
        users_qs = (
            Users.objects
            .filter(query)
            .select_related('profile_id')
            .order_by('user_id')
        )

        # ── Pagination ────────────────────────────────────────────────────────
        paginator = Paginator(users_qs, 7)

        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            return Response({'detail': 'Page out of range.'}, status=status.HTTP_404_NOT_FOUND)

        # ── Ratings: batch in one query to avoid N+1 ─────────────────────────
        user_ids = [u.user_id for u in page_obj.object_list]
        ratings  = (
            Rating.objects
            .filter(rated_to__in=user_ids)
            .values('rated_to')
            .annotate(avg_score=Avg('score'))
        )
        rating_map = {r['rated_to']: round(r['avg_score'], 2) for r in ratings}

        # ── Serialize ─────────────────────────────────────────────────────────
        user_list = [
            {
                'id':       user.user_id,
                'name':     user.get_full_name_from_userModel(),
                'contact':  user.phone,
                'location': f"{user.profile_id.municipal}, {user.profile_id.district}",
                'rating':   rating_map.get(user.user_id, 0.0),
                'status':   user.profile_status,
            }
            for user in page_obj.object_list
        ]

        return Response(
            {
                'users':        user_list,
                'total':        paginator.count,
                'total_pages':  paginator.num_pages,
                'current_page': page_obj.number,
                'has_next':     page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            },
            status=status.HTTP_200_OK,
        )
        ''''''

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
##########################################################################################
#                            Search USer End
##########################################################################################

##########################################################################################
#                            User Farmer Page
##########################################################################################
@api_view(['POST'])
@permission_classes([HasValidTokenForUser, IsAdmin])
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

##########################################################################################
#                            User Consumer Page
##########################################################################################
@api_view(['POST'])
@permission_classes([HasValidTokenForUser, IsAdmin])
def user_consumer_page(request):
    try:
        consumers = Users.objects.filter(Q(profile_id__user_type='Consumer') | Q(profile_id__user_type='VerifiedConsumer'))
    except Users.DoesNotExist:
        return Response({'error': 'Consumer not found'}, status=status.HTTP_404_NOT_FOUND)
    total_consumer = consumers.count()
    
    activated_consumer = consumers.filter(profile_status='ACTIVATED').count()
    
    verified_consumer = consumers.filter(profile_id__user_type='VerifiedFarmer').count()

    verification_pending_consumer = Verification.objects.filter(
        user_id__in=consumers, status='PENDING'
    ).count()


    return Response({
        'total_consumer': total_consumer,
        'activated_consumer': activated_consumer,
        'verified_consumer': verified_consumer,
        'verification_pending_consumer': verification_pending_consumer,
        }, status=status.HTTP_200_OK)

 
##########################################################################################
#                            User Consumer Page End
##########################################################################################
##########################################################################################
#                            Admin Page for Admin
##########################################################################################
from django.core.paginator import Paginator, EmptyPage

PAGE_SIZE = 7

@api_view(['POST'])
@permission_classes([HasValidTokenForUser, IsAdmin])
def admin_list(request):
    search_term    = request.data.get('search_data', '')
    profile_status = request.data.get('profile_status', '')      # 'PENDING' | 'ACTIVATED' | 'SUSPENDED' | 'DEACTIVATE'
    user_type      = request.data.get('user_type', '')           # 'Admin' | 'SuperAdmin'
    page           = request.data.get('page', 1)

    # ── Base queryset ────────────────────────────────────────────────────────
    qs = (
        Users.objects
        .filter(is_admin=True)   # profile_id is the FK → UsersProfile
        .order_by('profile_id__f_name', 'profile_id__m_name', 'profile_id__l_name')
    )

    # ── Filters ──────────────────────────────────────────────────────────────
    if profile_status.lower() != 'all status':
        qs = qs.filter(profile_status=profile_status)

    if user_type.lower() !='all admins':
        qs = qs.filter(profile_id__user_type=user_type)

    # ── Search (by name tokens or user_id) ───────────────────────────────────
    if search_term != '' or search_term != None:
        qs = qs.filter(
            Q(user_id__icontains=search_term)
            | Q(profile_id__f_name__icontains=search_term)
            | Q(profile_id__m_name__icontains=search_term)
            | Q(profile_id__l_name__icontains=search_term)
            | Q(profile_id__email__icontains=search_term)
            | Q(phone__icontains=search_term)
        )

    # ── Pagination ───────────────────────────────────────────────────────────
    paginator = Paginator(qs, PAGE_SIZE)

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        return Response(
            {'detail': 'Page out of range.'},
            status=status.HTTP_404_NOT_FOUND
        )

    # ── Serialize ────────────────────────────────────────────────────────────
    admins = [
        {
            'user_type':   user.profile_id.user_type,
            'id': user.user_id,
            'name': user.get_full_name_from_userModel(),
            'contact': user.phone,
            'location': f"{user.profile_id.municipal}, {user.profile_id.district}",
            'status': user.profile_status,  
        }
        for user in page_obj.object_list
    ]

    return Response(
        {
            'admins':       admins,
            'total':        paginator.count,          # total matching records
            'total_pages':  paginator.num_pages,
            'current_page': page_obj.number,
            'has_next':     page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        },
        status=status.HTTP_200_OK,
    )

@api_view(['POST'])
@permission_classes([HasValidTokenForUser, IsAdmin])
def user_admin_page(request):
    try:
        admins_obj = Users.objects.filter(is_admin=True)
    except Users.DoesNotExist:
        return Response({'error': 'Admin not found'}, status=status.HTTP_404_NOT_FOUND)
    #total_admin = admins.count()
    total_admins = admins_obj.count()
    super_admin = admins_obj.filter(prfile_id__user_type='SuperAdmin').count()
    admin = admins_obj.filter(prfile_id__user_type='Admin').count()

    return Response({
        'total_admins': total_admins,
        'no_of_admin': admin,
        'no_of_super_admin': super_admin,
        }, status=status.HTTP_200_OK)
##########################################################################################
#                            User Admin Page for Admin
##########################################################################################

##########################################################################################
#                            Wallet History Start
##########################################################################################
def transcation_history_fun(user_id, to_date = None, from_date = None, page = 1):
    try:
        # page size = until not ended & rows = 15 per page
        user = Users.objects.get(user_id = user_id)
        query = Q()
        if user_id != None:
            query &= (Q(initiated_by =user) | Q(transaction_to = user) )
        if to_date != None and from_date != None:
            query &= Q(transaction_date__range=[from_date, to_date])
        
        transactions = Transaction.objects.filter(query).order_by('-transaction_date')
        
        from django.core.paginator import Paginator
        paginator = Paginator(transactions, 15)
        page_obj = paginator.get_page(page)

        return {
            "page": page,
            "total_pages": paginator.num_pages,
            "results": list(page_obj.object_list.values())
        }

        return ""
    except Transaction.DoesNotExist:
        return None
    
@api_view(['POST'])
@permission_classes([HasValidTokenForUser, IsAdmin])
def get_transaction_history_admin(request):
    user_id = request.data.get('user_id')
    to_date = request.data.get('to_date', None)
    from_date = request.data.get('from_date', None)
    page = request.data.get('page', 1)
    transcation_history = transcation_history_fun(user_id, to_date, from_date, page)

    if transcation_history is None:
        return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(transcation_history, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def get_transaction_history_user(request):
    user_id = request.headers.get('user_id')
    to_date = request.data.get('to_date', None)
    from_date = request.data.get('from_date', None)
    page = request.data.get('page', 1)
    transcation_history = transcation_history_fun(user_id, to_date, from_date, page)
    
    if transcation_history is None:
        return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(transcation_history, status=status.HTTP_200_OK)

##########################################################################################
#                            Wallet History End
##########################################################################################
