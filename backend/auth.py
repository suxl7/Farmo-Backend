from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from backend.models import Tokens

class CustomTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # Extract header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None  # No token provided

        token = parts[1]

        # Validate token
        try:
            user_token = Tokens.objects.get(token=token)
        except Tokens.DoesNotExist:
            raise AuthenticationFailed('Invalid token')

        if user_token.expires_at < timezone.now() and user_token.token_status != "ACTIVE":
            raise AuthenticationFailed('Token expired')

        # Return user so DRF attaches it to request.user
        return (user_token.user, None)