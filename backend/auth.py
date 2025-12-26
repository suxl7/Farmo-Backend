from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from backend.models import Tokens

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