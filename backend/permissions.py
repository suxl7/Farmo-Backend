from rest_framework import permissions
from .models import Connections
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Tokens



class IsOwnerOrReadOnly(permissions.BasePermission):
    """Allow read access to all, write access only to owner"""
    
    def has_object_permission(self, request, view, obj):
        # Allow GET, HEAD, OPTIONS requests to anyone
        if request.method in permissions.SAFE_METHODS:
            return True
        # Only owner can modify
        return obj.user == request.user


class ConnectionOnly(permissions.BasePermission):
    """Allow access only if requester is connected to target user"""

    def has_object_permission(self, request, view, obj):
        # obj here will be the target user whose status is being checked
        return Connections.objects.filter(
            user=request.user,
            target_user=obj,
            status="ACCEPTED"
        ).exists() or Connections.objects.filter(
            user=obj,
            target_user=request.user,
            status="ACCEPTED"
        ).exists()



class IsWalletOwner(permissions.BasePermission):
    """Allow access only to wallet owner"""
    
    def has_object_permission(self, request, view, obj):
        # Only wallet owner can access
        return obj.user == request.user
    


class CustomTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None

        token = parts[1]

        try:
            token_obj = Tokens.objects.get(token=token)
        except Tokens.DoesNotExist:
            raise AuthenticationFailed('Invalid token')

        if token_obj.token_status != 'ACTIVE':
            raise AuthenticationFailed(f'Token is {token_obj.token_status.lower()}')

        if token_obj.expires_at < timezone.now():
            raise AuthenticationFailed('Token expired')

        return (token_obj.user_id, None)

class TokenAuthentication(CustomTokenAuthentication):
    pass

class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        auth = CustomTokenAuthentication()
        try:
            user_auth = auth.authenticate(request)
            if user_auth is not None:
                request.user = user_auth[0]
                return True
        except AuthenticationFailed:
            return False
        return False
