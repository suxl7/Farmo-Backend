# Custom Token Authentication System - Farmo Backend

## Overview
This document describes the custom token-based authentication system implemented for the Farmo Django REST Framework project.

## Architecture

### 1. Token Model (`backend/models.py`)
The `Tokens` model stores authentication tokens with the following fields:
- `user_id`: ForeignKey to Users model
- `token`: Unique token string (32-byte URL-safe)
- `refresh_token`: Refresh token string
- `device_info`: Device information (optional)
- `issued_at`: Token creation timestamp
- `expires_at`: Token expiration timestamp
- `token_status`: Token status (ACTIVE/INACTIVE)

#### Token Expiry Rules:
- **Admin users**: 1 day
- **Farmers/Consumers**: 40 days

#### Class Method:
```python
Tokens.create_token(user, days=40)
```
Generates a random token with specified expiry days.

### 2. Authentication Service (`backend/service_frontend/authentication.py`)

#### Login Endpoint: `/api/auth/login/`
**Method**: POST  
**Permission**: AllowAny  
**Request Body**:
```json
{
  "identifier": "user_id or phone",
  "password": "password",
  "is_admin": false,
  "device_info": "device details"
}
```

**Success Response** (200):
```json
{
  "login_access": true,
  "token": "token_string",
  "refresh_token": "refresh_token_string",
  "user_id": "user_id"
}
```

**Error Responses**:
- 400: Missing credentials
- 401: Invalid credentials
- 403: Account pending/inactive

#### Login with Token: `/api/auth/login-with-token/`
**Method**: POST  
**Permission**: AllowAny  
**Request Body**:
```json
{
  "token": "existing_token",
  "refresh_token": "existing_refresh_token",
  "user_id": "user_id",
  "device_info": "device details"
}
```

**Behavior**:
- If token is valid and not expired: Returns same token
- If token is expired: Generates new token pair
- If token is invalid: Returns 401 error

#### Token Management Rules:
- Maximum 2 active tokens per user
- When creating 3rd token, oldest token is deactivated
- Tokens are device-specific

### 3. Custom Authentication Class (`backend/auth.py`)

#### `CustomTokenAuthentication`
Extends `rest_framework.authentication.BaseAuthentication`

**How it works**:
1. Extracts token from `Authorization: Bearer <token>` header
2. Validates token exists in database with ACTIVE status
3. Checks token expiry date
4. Returns `(user, None)` if valid
5. Raises `AuthenticationFailed` if invalid or expired

**Usage**: Automatically applied to all views via `settings.py`

### 4. Settings Configuration (`Farmo/settings.py`)

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'backend.auth.CustomTokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

This configuration:
- Applies token authentication to ALL endpoints by default
- Requires authentication for ALL endpoints by default
- Use `@permission_classes([AllowAny])` to make endpoints public

### 5. Protected Views (`backend/views.py`)

#### Example: Profile View
```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    user = request.user  # Authenticated user available here
    # ... view logic
```

**Available Protected Endpoints**:
- `/api/user/profile/` - Get user profile
- `/api/protected/` - Example protected endpoint
- `/api/wallet/verify-pin/` - Verify wallet PIN
- `/api/user/update-profile-picture/` - Update profile picture
- `/api/user/verification-request/` - Submit verification documents
- `/api/user/online-status/` - Get user online status

## Client Usage

### 1. Login Flow
```javascript
// Step 1: Login
const response = await fetch('/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    identifier: 'user123',
    password: 'password',
    is_admin: false,
    device_info: 'Chrome/Windows'
  })
});

const data = await response.json();
// Store token and refresh_token
localStorage.setItem('token', data.token);
localStorage.setItem('refresh_token', data.refresh_token);
localStorage.setItem('user_id', data.user_id);
```

### 2. Making Authenticated Requests
```javascript
const token = localStorage.getItem('token');

const response = await fetch('/api/user/profile/', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### 3. Remember Me (Auto-login)
```javascript
const token = localStorage.getItem('token');
const refresh_token = localStorage.getItem('refresh_token');
const user_id = localStorage.getItem('user_id');

const response = await fetch('/api/auth/login-with-token/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    token,
    refresh_token,
    user_id,
    device_info: 'Chrome/Windows'
  })
});

const data = await response.json();
if (data.login_access) {
  // Update tokens if new ones were issued
  if (data.token !== token) {
    localStorage.setItem('token', data.token);
    localStorage.setItem('refresh_token', data.refresh_token);
  }
}
```

## Security Features

### 1. Token Security
- Tokens are 32-byte URL-safe random strings
- Stored hashed in database (via secrets.token_urlsafe)
- Automatic expiry enforcement
- Device-specific tokens

### 2. Password Security
- Passwords hashed using Django's `make_password`
- Verified using `check_password`
- Never stored in plain text

### 3. Wallet PIN Security
- 4-digit PINs hashed using Django's `make_password`
- Verified using `check_password`
- Separate from user password

### 4. Rate Limiting
```python
'DEFAULT_THROTTLE_RATES': {
    'anon': '100/hour',
    'user': '1000/hour'
}
```

## Error Handling

### Authentication Errors
- **Invalid token**: 401 Unauthorized
- **Token expired**: 401 Unauthorized
- **Missing token**: 401 Unauthorized
- **Account inactive**: 403 Forbidden
- **Account pending**: 403 Forbidden

### Common Error Codes
- `MISSING_CREDENTIALS`: Required fields missing
- `INVALID_CREDENTIALS`: Wrong username/password
- `ACCOUNT_PENDING`: Account awaiting approval
- `ACCOUNT_INACTIVE`: Account deactivated
- `INVALID_TOKENS`: Token not found or invalid

## Database Schema

### Tokens Table
```sql
CREATE TABLE backend_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id_id VARCHAR(20) REFERENCES backend_users(user_id),
    token TEXT NOT NULL,
    refresh_token TEXT,
    device_info VARCHAR(255),
    issued_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    token_status VARCHAR(20) DEFAULT 'ACTIVE'
);
```

## Testing

### Test Login
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "user123",
    "password": "password",
    "is_admin": false,
    "device_info": "curl"
  }'
```

### Test Protected Endpoint
```bash
curl -X GET http://localhost:8000/api/user/profile/ \
  -H "Authorization: Bearer <your_token>"
```

## Migration

To apply the token model changes:
```bash
py manage.py makemigrations
py manage.py migrate
```

## Files Modified/Created

### Modified:
1. `backend/models.py` - Added `create_token` class method
2. `backend/auth.py` - Fixed authentication logic
3. `backend/service_frontend/authentication.py` - Updated token expiry logic
4. `Farmo/settings.py` - Configured REST_FRAMEWORK settings
5. `Farmo/urls.py` - Added protected view routes

### Created:
1. `backend/views.py` - Protected view examples
2. `AUTHENTICATION_GUIDE.md` - This documentation

## Best Practices

1. **Always use HTTPS in production** to protect tokens in transit
2. **Store tokens securely** on client side (httpOnly cookies preferred)
3. **Implement token refresh** before expiry for better UX
4. **Clear tokens on logout** from both client and server
5. **Monitor token usage** for suspicious activity
6. **Rotate tokens regularly** for admin users

## Troubleshooting

### Token not working
- Check token is in `Authorization: Bearer <token>` format
- Verify token exists in database with ACTIVE status
- Check token hasn't expired
- Ensure user account is ACTIVE

### Multiple device login issues
- Each device gets its own token
- Maximum 2 active tokens per user
- Oldest token auto-deactivated when limit reached

## Future Enhancements

1. Token blacklisting on logout
2. Token refresh endpoint
3. Multi-factor authentication
4. IP-based token validation
5. Suspicious activity detection
