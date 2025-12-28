from rest_framework import permissions
from .models import Connections
from django.utils import timezone
from rest_framework.permissions import BasePermission
from django.db.models import Q
from .models import Tokens


# WORK on POST Method only 
class ConnectionOnly(BasePermission):
    """Allow access only if requester is connected to target user in body"""

    def has_permission(self, request, view):
        
        requester_id = request.headers.get("userid")
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
        # Authorization: token <token_value>
        # userid: <user_id>
        auth_header = request.headers.get("Authorization")
        user_id = request.headers.get("userid")

        if not auth_header or not auth_header.startswith("token "):
            return False
        if not user_id:
            return False

        token_value = auth_header.split()[1]

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
