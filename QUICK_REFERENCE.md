# Token Authentication - Quick Reference

## Token Expiry Times
- **Admin**: 1 day
- **Farmer/Consumer**: 40 days

## Creating Protected Views

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_protected_view(request):
    user = request.user  # Authenticated user
    return Response({'user_id': user.user_id})
```

## Creating Public Views

```python
from rest_framework.permissions import AllowAny

@api_view(['POST'])
@permission_classes([AllowAny])
def my_public_view(request):
    # No authentication required
    return Response({'message': 'Public endpoint'})
```

## Client-Side Usage

### Login
```javascript
const response = await fetch('/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    identifier: 'user123',
    password: 'password',
    is_admin: false,
    device_info: 'Browser/OS'
  })
});
const { token, refresh_token, user_id } = await response.json();
```

### Authenticated Request
```javascript
const response = await fetch('/api/user/profile/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

## Token Management

### Generate Token (Backend)
```python
from backend.models import Tokens

# For admin (1 day)
token = Tokens.create_token(user, days=1)

# For farmer/consumer (40 days)
token = Tokens.create_token(user, days=40)
```

### Check Token Status (Backend)
```python
from backend.models import Tokens
from django.utils import timezone

token_obj = Tokens.objects.get(token=token_string)
is_valid = (
    token_obj.token_status == 'ACTIVE' and 
    token_obj.expires_at > timezone.now()
)
```

## Common Error Codes

| Code | Meaning | HTTP Status |
|------|---------|-------------|
| `MISSING_CREDENTIALS` | Username/password not provided | 400 |
| `INVALID_CREDENTIALS` | Wrong username/password | 401 |
| `ACCOUNT_PENDING` | Account awaiting approval | 403 |
| `ACCOUNT_INACTIVE` | Account deactivated | 403 |
| `INVALID_TOKENS` | Token not found/invalid | 401 |

## API Endpoints

### Public (No Token Required)
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login with credentials
- `POST /api/auth/login-with-token/` - Login with existing token

### Protected (Token Required)
- `GET /api/user/profile/` - Get user profile
- `PUT /api/user/update-profile-picture/` - Update profile picture
- `POST /api/user/verification-request/` - Submit verification
- `POST /api/user/online-status/` - Get online status
- `POST /api/wallet/verify-pin/` - Verify wallet PIN
- `POST /api/auth/check-userid/` - Check user ID availability

## Testing with cURL

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"identifier":"user123","password":"pass","is_admin":false,"device_info":"curl"}'
```

### Protected Endpoint
```bash
curl -X GET http://localhost:8000/api/user/profile/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Troubleshooting

### "Invalid token" error
- Check token format: `Authorization: Bearer <token>`
- Verify token exists in database
- Check token_status is 'ACTIVE'
- Verify token hasn't expired

### "Authentication credentials were not provided"
- Missing Authorization header
- Wrong header format (must be `Bearer <token>`)

### Token expired too quickly
- Admin tokens: 1 day (by design)
- Use login-with-token to refresh

## Security Best Practices

1. ✅ Always use HTTPS in production
2. ✅ Store tokens securely (httpOnly cookies preferred)
3. ✅ Clear tokens on logout
4. ✅ Don't log tokens
5. ✅ Implement token refresh before expiry
6. ✅ Monitor for suspicious activity

## Files to Know

- `backend/models.py` - Tokens model
- `backend/auth.py` - Authentication class
- `backend/service_frontend/authentication.py` - Login logic
- `Farmo/settings.py` - Authentication config
- `AUTHENTICATION_GUIDE.md` - Full documentation
- `CHANGES_SUMMARY.md` - All changes made
