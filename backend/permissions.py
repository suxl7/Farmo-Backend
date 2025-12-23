from rest_framework import permissions
from .models import Connections

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
