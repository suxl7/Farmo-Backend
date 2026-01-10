from rest_framework import permissions
from .models import Connections
from django.utils import timezone
from rest_framework.permissions import BasePermission
from django.db.models import Q
from .models import Tokens, Users


# WORK on POST Method only 
class ConnectionOnly(BasePermission):
    """Allow access only if requester is connected to target user in body"""

    def has_permission(self, request, view):
        
        requester_id = request.headers.get("user_id")
        target_id = request.data.get("target_user")

        if not requester_id or not target_id:
            return False

        # Use Q objects for single query
        return Connections.objects.filter(
            Q(user_id=requester_id, target_user_id=target_id) | 
            Q(user_id=target_id, target_user_id=requester_id),
            status="ACCEPTED"
        ).exists()


class HasValidTokenForUser(BasePermission):
    """
    Permission that checks if the provided token belongs to the given user_id
    and is still active + not expired.
    """

    def has_permission(self, request, view):
        # Expect frontend to send both headers:
        # token: <token_value>
        # user_id: <user_id>
        token_value = request.headers.get("token")
        user_id = request.headers.get("user_id")

        if not token_value or not user_id:
            return False

        try:
            token_obj = Tokens.objects.get(token=token_value, user_id__user_id=user_id)
        except Tokens.DoesNotExist:
            return False

        # Check token status and expiry
        if token_obj.token_status != "ACTIVE":
            return False
        if token_obj.expires_at < timezone.now():
            return False

        return True


class IsFarmer(BasePermission):
    """Allow access only if requester is a farmer"""

    def has_permission(self, request, view):
        # Expect frontend to send headers:
        # user_id: <user_id>
        user_id = request.headers.get("user_id")

        if not user_id:
            return False
        
        user_type = Users.objects.get(user_id=user_id).profile_id.user_type

        if user_type == "Farmer" or user_type == "VerifiedFarmer":
            return True
        
        return False
      
class IsConsumer(BasePermission):
    """Allow access only if requester is a consumer"""

    def has_permission(self, request, view):
        # Expect frontend to send headers:
        # user_id: <user_id>
        user_id = request.headers.get("user_id")

        if not user_id:
            return False

        user_type = Users.objects.get(user_id=user_id).profile_id.user_type
        if user_type == "Consumer" or user_type == "VerifiedConsumer":
            return True

        return False

class IsAdmin(BasePermission):
    """Allow access only if requester is an admin"""

    def has_permission(self, request, view):
        # Expect frontend to send headers:
        # user_id: <user_id>
        user_id = request.headers.get("user_id")

        if not user_id:
            return False

        user = Users.objects.get(user_id=user_id)
        if user.is_admin:
            return True

        return False
    
class IsSuperAdmin(BasePermission):
    """Allow access only if requester is a consumer"""

    def has_permission(self, request, view):
        # Expect frontend to send headers:
        # user_id: <user_id>
        user_id = request.headers.get("user_id")

        if not user_id :
            return False

        user_type = Users.objects.get(user_id=user_id).profile_id.user_type
        if user_type == "SuperAdmin":
            return True

        return False
    


class IsVerifiedConsumer(BasePermission):
    """Allow access only if requester is a consumer"""

    def has_permission(self, request, view):
        # Expect frontend to send headers:
        # user_id: <user_id>
        user_id = request.headers.get("user_id")

        if not user_id:
            return False

        user = Users.objects.select_related('profile_id').get(user_id=user_id)
        user_type = user.profile_id.user_type
        if user_type == "VerifiedConsumer":
            return True

        return False
    
class IsVerifiedFarmer(BasePermission):
    """Allow access only if requester is a consumer"""

    def has_permission(self, request, view):
        # Expect frontend to send headers:
        # user_id: <user_id>
        user_id = request.headers.get("user_id")

        if not user_id:
            return False

        user = Users.objects.select_related('profile_id').get(user_id=user_id)
        user_type = user.profile_id.user_type
        if user_type == "VerifiedFarmer":
            return True

        return False