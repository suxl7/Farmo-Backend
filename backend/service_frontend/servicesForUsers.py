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
                'rating':   round(rating_map.get(user.user_id) if user.user_id in rating_map else 0.0,1),
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
# @permission_classes([HasValidTokenForUser, IsAdmin])
@permission_classes([AllowAny])
def admin_list(request):
    search_term    = request.data.get('search_data', '')
    profile_status = request.data.get('profile_status', '')      # 'PENDING' | 'ACTIVATED' | 'SUSPENDED' | 'DEACTIVATE'
    user_type      = request.data.get('user_type', '')           # 'Admin' | 'SuperAdmin'
    page           = request.data.get('page', 1)

    # ── Base queryset ────────────────────────────────────────────────────────
    qs = (
        Users.objects
        .filter(is_admin=True)
        .order_by('profile_id__f_name', 'profile_id__m_name', 'profile_id__l_name')
    )

    # ── Filters ──────────────────────────────────────────────────────────────
    if profile_status not in ['all status', '', 'All Status', 'All', 'all']:
        qs = qs.filter(profile_status=profile_status)

    if user_type.lower() != 'all admins':
        qs = qs.filter(profile_id__user_type=user_type)

    # ── Search (by name tokens or user_id) ───────────────────────────────────
    if search_term:   # ✅ Fixed: was `!= '' or != None` (always True)
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
            'user_type': user.profile_id.user_type,
            'id':        user.user_id,
            'name':      user.get_full_name_from_userModel(),
            'contact':   user.phone,
            'location':  f"{user.profile_id.municipal}, {user.profile_id.district}",
            'status':    user.profile_status,
        }
        for user in page_obj.object_list
    ]

    return Response(
        {
            'admins':       admins,
            'total':        paginator.count,
            'total_pages':  paginator.num_pages,
            'current_page': page_obj.number,
            'has_next':     page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        },
        status=status.HTTP_200_OK,
    )

@api_view(['POST'])
#@permission_classes([HasValidTokenForUser, IsAdmin])
@permission_classes([AllowAny])
def user_admin_page(request):
    admins_obj = Users.objects.filter(is_admin=True)

    total_admins = admins_obj.count()
    super_admin  = admins_obj.filter(profile_id__user_type='SuperAdmin').count()
    admin        = admins_obj.filter(profile_id__user_type='Admin').count()

    return Response({
        'total_admins':     total_admins,
        'no_of_admin':      admin,
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

##########################################################################################
#                            Acction Status Action Start
##########################################################################################
@api_view(['POST'])
@permission_classes([HasValidTokenForUser, IsAdmin])
#@permission_classes([AllowAny])
def action_status_action(request):
    user_id = request.data.get('target_user_id')
    action = request.data.get('action') # suspend, activate, or deactivate
    
    # Add .lower() here to catch uppercase inputs early, just to be safe!
    if not action:
        return Response({'error': 'Action is required'}, status=status.HTTP_400_BAD_REQUEST)
        
    action_lower = action.lower()

    try:
        # ADD 'deactivate' to this list
        if action_lower not in ['suspend', 'activate', 'deactivate']:
            return Response({'error': 'Invalid Action For User'}, status=status.HTTP_400_BAD_REQUEST)
            
        user = Users.objects.get(user_id=user_id)
        
        if action_lower == 'suspend':
            user.profile_status = 'SUSPENDED'
        elif action_lower == 'activate':
            user.profile_status = 'ACTIVATED'
        elif action_lower == 'deactivate':
            user.profile_status = 'DEACTIVATED'
            
        user.save()
        return Response({}, status=status.HTTP_200_OK)
        
    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
##########################################################################################
#                            Acction Status Action End
##########################################################################################
##########################################################################################
#                            Wallet History End
##########################################################################################
##########################################################################################
#                            Wallet History End
##########################################################################################


@api_view(['POST'])
@permission_classes([AllowAny, IsAdmin])
def update_admin_profile(request):
    from backend.utils.whatsapp import normalize_whatsapp
    userid = request.data.get('user_id')
    data = request.data

    phone = data.get("phone")
    phone2 = data.get("phone2")
    facebook = data.get("facebook")
    whatsapp = data.get("whatsapp")
    email = data.get("email")

   
    if not email or not phone :
        return Response({"error": "Required fields are missing."}, status=status.HTTP_400_BAD_REQUEST)
    
    
    try:
        user = Users.objects.get(user_id=userid, is_admin=True)
        profile = UsersProfile.objects.get(profile_id=user.profile_id.profile_id)
        profile.phone02 = phone2
        profile.facebook = facebook
        profile.whatsapp = normalize_whatsapp(whatsapp) if whatsapp else None
        profile.email = email
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

##########################################################################################
#                            Wallet History End
##########################################################################################


##########################################################################################
#                            Search Users by Location Start
##########################################################################################
from backend.permissions import IsFarmerOrConsumer

@api_view(['POST'])
@permission_classes([AllowAny, IsFarmerOrConsumer])
def search_users_from_app(request):
    import os
    import base64
    import cv2
    
    user_id = request.headers.get('user-id')
    search = request.data.get('search', '').strip()
    address = request.data.get('address', '').strip()
    page = request.data.get('page', 1)
    
    # Return empty if no search criteria
    if not search and not address:
        return Response({
            'users': [],
            'total': 0,
            'total_pages': 0,
            'current_page': 1,
            'has_next': False,
            'has_previous': False
        }, status=status.HTTP_200_OK)
    
    try:
        current_user = Users.objects.select_related('profile_id').get(user_id=user_id)
        profile = current_user.profile_id
        
        query = Q(is_admin=False)
        
        if search:
            search_terms = search.split()
            name_query = Q()
            for term in search_terms:
                name_query |= (
                    Q(profile_id__f_name__icontains=term) |
                    Q(profile_id__m_name__icontains=term) |
                    Q(profile_id__l_name__icontains=term)
                )
            query &= (name_query | Q(user_id__icontains=search) | Q(phone__icontains=search))
        
        if address:
            query &= (
                Q(profile_id__tole__icontains=address) |
                Q(profile_id__ward__icontains=address) |
                Q(profile_id__municipal__icontains=address) |
                Q(profile_id__district__icontains=address) |
                Q(profile_id__province__icontains=address)
            )
            users = Users.objects.filter(query).select_related('profile_id')[:10 * int(page)]
        else:
            users = Users.objects.filter(query).select_related('profile_id')
            
            same_tole = []
            same_ward = []
            same_municipal = []
            same_district = []
            same_province = []
            others = []
            
            for u in users:
                p = u.profile_id
                if p.tole == profile.tole and p.ward == profile.ward and p.municipal == profile.municipal:
                    same_tole.append(u)
                elif p.ward == profile.ward and p.municipal == profile.municipal:
                    same_ward.append(u)
                elif p.municipal == profile.municipal:
                    same_municipal.append(u)
                elif p.district == profile.district:
                    same_district.append(u)
                elif p.province == profile.province:
                    same_province.append(u)
                else:
                    others.append(u)
            
            users = same_tole + same_ward + same_municipal + same_district + same_province + others
        
        from django.core.paginator import Paginator
        paginator = Paginator(users, 10)
        page_obj = paginator.get_page(page)
        
        data = []
        for u in page_obj:
            from django.conf import settings
            
            profile_pic_data = {
                'user_id': u.user_id,
                'full_name': u.get_full_name_from_userModel(),
                'file': None,
                'size': 0,
                'mime_type': None,
                'file_type': 'img'
            }
            
            if u.profile_id.profile_url:
                file_path = os.path.join(settings.MEDIA_ROOT, u.profile_id.profile_url)
            else:
                user_type = u.profile_id.user_type.lower()
                default_map = {
                    'verifiedfarmer': 'pp-farmer.png',
                    'farmer': 'pp-farmer.png',
                    'verifiedconsumer': 'pp-consumer.png',
                    'consumer': 'pp-consumer.png',
                    'admin': 'pp-admin.png',
                    'superadmin': 'pp-superadmin.png',
                }
                filename = default_map.get(user_type, 'pp-guest.png')
                file_path = f'backend/static/DefaultProfilePicture/{filename}'
            
            try:
                if os.path.exists(file_path):
                    img = cv2.imread(file_path)
                    if img is not None:
                        h, w = img.shape[:2]
                        scale = min(100 / w, 100 / h)
                        new_w = int(w * scale)
                        new_h = int(h * scale)
                        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                        _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 70])
                        profile_pic_data['file'] = base64.b64encode(buffer).decode('utf-8')
                        profile_pic_data['size'] = round(len(buffer) / (1024 * 1024), 3)
                        profile_pic_data['mime_type'] = 'image/jpeg'
            except Exception:
                pass
            
            data.append(profile_pic_data)
        
        return Response({
            'users': data,
            'total': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }, status=status.HTTP_200_OK)
        
    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

##########################################################################################
#                            Search Users by Location End
##########################################################################################

##########################################################################################
#                            Connection List Start
##########################################################################################
from django.conf import settings
@api_view(['POST'])
@permission_classes([AllowAny, IsFarmerOrConsumer])
def get_connection_list(request):
    import os
    import base64
    import cv2
    from backend.models import Connections
    
    user_id = request.headers.get('user-id')
    conn_type = request.data.get('type', 'connected')
    page = request.data.get('page', 1)
    page_size = request.data.get('page_size', 20)
    
    if conn_type not in ['connected', 'sent', 'pending']:
        return Response({'error': 'Invalid type. Must be connected, sent, or pending'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = Users.objects.get(user_id=user_id)
        
        if conn_type == 'connected':
            connections = Connections.objects.filter(
                Q(user=user, status='ACCEPTED') | Q(target_user=user, status='ACCEPTED')
            ).select_related('user__profile_id', 'target_user__profile_id')
        elif conn_type == 'sent':
            connections = Connections.objects.filter(
                user=user, status='PENDING'
            ).select_related('target_user__profile_id')
        else:  # pending
            connections = Connections.objects.filter(
                target_user=user, status='PENDING'
            ).select_related('user__profile_id')
        
        from django.core.paginator import Paginator
        paginator = Paginator(connections, page_size)
        page_obj = paginator.get_page(page)
        
        results = []
        for conn in page_obj:
            if conn_type == 'connected':
                other_user = conn.target_user if conn.user.user_id == user_id else conn.user
            elif conn_type == 'sent':
                other_user = conn.target_user
            else:
                other_user = conn.user
            
            profile = other_user.profile_id
            
            from django.conf import settings
            if profile.profile_url:
                file_path = os.path.join(settings.MEDIA_ROOT, profile.profile_url)
            else:
                user_type_lower = profile.user_type.lower()
                default_map = {
                    'verifiedfarmer': 'pp-farmer.png',
                    'farmer': 'pp-farmer.png',
                    'verifiedconsumer': 'pp-consumer.png',
                    'consumer': 'pp-consumer.png',
                }
                filename = default_map.get(user_type_lower, 'pp-guest.png')
                file_path = f'backend/static/DefaultProfilePicture/{filename}'
            
            profile_pic = None
            try:
                if os.path.exists(file_path):
                    img = cv2.imread(file_path)
                    if img is not None:
                        h, w = img.shape[:2]
                        scale = min(100 / w, 100 / h)
                        new_w = int(w * scale)
                        new_h = int(h * scale)
                        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                        _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 70])
                        profile_pic = base64.b64encode(buffer).decode('utf-8')
            except Exception:
                pass
            
            results.append({
                'user_id': other_user.user_id,
                'full_name': other_user.get_full_name_from_userModel(),
                'profile_pic': profile_pic,
                'status': conn_type
            })
        
        return Response({
            'total_count': paginator.count,
            'page': page_obj.number,
            'has_next': page_obj.has_next(),
            'results': results
        }, status=status.HTTP_200_OK)
        
    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

##########################################################################################
#                            Connection List End
##########################################################################################

##########################################################################################
#                            Search Users for Android Start
##########################################################################################

@api_view(['POST'])
@permission_classes([AllowAny, IsFarmerOrConsumer])
def search_users_android(request):
    import os
    import base64
    import cv2
    from backend.models import Connections
    
    user_id = request.headers.get('user-id')
    search = request.data.get('search', '').strip()
    address = request.data.get('address', '').strip()
    page = request.data.get('page')
    
    if not search and not address:
        return Response({'users': []}, status=status.HTTP_200_OK)
    
    try:
        current_user = Users.objects.get(user_id=user_id)
        profile = current_user.profile_id
        
        # Get all connected user IDs
        connected_ids = set(
            Connections.objects.filter(
                Q(user=current_user, status='ACCEPTED') | Q(target_user=current_user, status='ACCEPTED')
            ).values_list('user_id', 'target_user_id')
        )
        connected_user_ids = {uid for pair in connected_ids for uid in pair if uid != current_user.user_id}
        
        query = Q(is_admin=False) & ~Q(user_id=user_id)
        
        if search:
            query &= (
                Q(user_id__icontains=search) |
                Q(profile_id__f_name__icontains=search) |
                Q(profile_id__m_name__icontains=search) |
                Q(profile_id__l_name__icontains=search)
            )
        
        if address:
            query &= (
                Q(profile_id__tole__icontains=address) |
                Q(profile_id__ward__icontains=address) |
                Q(profile_id__municipal__icontains=address) |
                Q(profile_id__district__icontains=address) |
                Q(profile_id__province__icontains=address)
            )
        
        users = Users.objects.filter(query).select_related('profile_id')
        
        same_ward = []
        same_municipal = []
        same_district = []
        others = []
        
        for u in users:
            p = u.profile_id
            if p.ward == profile.ward and p.municipal == profile.municipal:
                same_ward.append(u)
            elif p.municipal == profile.municipal:
                same_municipal.append(u)
            elif p.district == profile.district:
                same_district.append(u)
            else:
                others.append(u)
        
        sorted_users = same_ward + same_municipal + same_district + others
        
        if page is not None:
            from django.core.paginator import Paginator
            paginator = Paginator(sorted_users, 20)
            page_obj = paginator.get_page(page)
            users_to_return = page_obj.object_list
        else:
            users_to_return = sorted_users[:10]
        
        results = []
        for u in users_to_return:
            # Determine file path
            if u.profile_id.profile_url:
                file_path = os.path.join(settings.MEDIA_ROOT, u.profile_id.profile_url)
            else:
                user_type = u.profile_id.user_type.lower()
                default_map = {
                    'verifiedfarmer': 'pp-farmer.png',
                    'farmer': 'pp-farmer.png',
                    'verifiedconsumer': 'pp-consumer.png',
                    'consumer': 'pp-consumer.png',
                }
                filename = default_map.get(user_type, 'pp-guest.png')
                file_path = f'backend/static/DefaultProfilePicture/{filename}'
            
            # Compress and encode profile picture
            profile_pic = None
            if os.path.exists(file_path):
                try:
                    img = cv2.imread(file_path)
                    if img is not None:
                        h, w = img.shape[:2]
                        scale = min(100 / w, 100 / h)
                        new_w = int(w * scale)
                        new_h = int(h * scale)
                        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                        _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 70])
                        profile_pic = base64.b64encode(buffer).decode('utf-8')
                except Exception as e:
                    print(f"Error compressing image for {u.user_id}: {e}")
            
            # Fallback to guest profile if compression failed
            if not profile_pic:
                try:
                    fallback_path = 'backend/static/DefaultProfilePicture/pp-guest.png'
                    if os.path.exists(fallback_path):
                        img = cv2.imread(fallback_path)
                        if img is not None:
                            h, w = img.shape[:2]
                            scale = min(100 / w, 100 / h)
                            new_w = int(w * scale)
                            new_h = int(h * scale)
                            resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                            _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 70])
                            profile_pic = base64.b64encode(buffer).decode('utf-8')
                except Exception:
                    pass
            
            results.append({
                'user_id': u.user_id,
                'name': u.get_full_name_from_userModel(),
                'profile_pic': profile_pic,
                'is_connected': u.user_id in connected_user_ids
            })
        
        response_data = {'users': results}
        if page is not None:
            response_data['current_page'] = page_obj.number
            response_data['total_pages'] = paginator.num_pages
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

##########################################################################################
#                            Search Users for Android End
##########################################################################################
