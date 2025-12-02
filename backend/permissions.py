from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Allow read access to all, write access only to owner"""
    
    def has_object_permission(self, request, view, obj):
        # Allow GET, HEAD, OPTIONS requests to anyone
        if request.method in permissions.SAFE_METHODS:
            return True
        # Only owner can modify
        return obj.user == request.user


class IsWalletOwner(permissions.BasePermission):
    """Allow access only to wallet owner"""
    
    def has_object_permission(self, request, view, obj):
        # Only wallet owner can access
        return obj.user == request.user
