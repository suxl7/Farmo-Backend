# class tokenVerification:
#     def verify_token(self, token, user_id):
#         """
#         Verify if the provided token is valid for the given user.

#         Args:
#             token (str): The token to verify.
#             user_id (int): The ID of the user associated with the token.

#         Returns:
#             bool: True if the token is valid and active for the user, False otherwise.
#         """
#         from backend.models import Tokens
#         try:
#             is_valid = Tokens.objects.filter(
#                 token=token,
#                 user_id=user_id,
#                 token_status="ACTIVE"
#             ).exists()
#             return is_valid
#         except Exception as e:
#             # Log the exception for debugging purposes
#             print(f"Error during token verification: {e}")
#             return False


from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from backend.models import UserToken

class TokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # Extract header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None  # No token provided

        token = parts[1]

        # Validate token
        try:
            user_token = UserToken.objects.get(token=token)
        except UserToken.DoesNotExist:
            raise AuthenticationFailed('Invalid token')

        if user_token.expires_at < timezone.now():
            raise AuthenticationFailed('Token expired')

        # Return user so DRF attaches it to request.user
        return (user_token.user, None)
