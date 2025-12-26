# Token Status Management Guide

## Token Status Types

Tokens can have three statuses:
- **ACTIVE**: Token is valid and can be used for authentication
- **INACTIVE**: Token has been deactivated (logged out)
- **SUSPENDED**: Token is temporarily suspended (can be reactivated)

## Token Model Methods

### Instance Methods

#### `token.suspend()`
Suspend a specific token (temporary deactivation).
```python
token = Tokens.objects.get(token=token_string)
token.suspend()
```

#### `token.deactivate()`
Permanently deactivate a token (logout).
```python
token = Tokens.objects.get(token=token_string)
token.deactivate()
```

#### `token.activate()`
Reactivate a suspended token.
```python
token = Tokens.objects.get(token=token_string)
token.activate()
```

### Class Methods

#### `Tokens.deactivate_all_user_tokens(user)`
Deactivate all active tokens for a user (logout from all devices).
```python
from backend.models import Tokens, Users

user = Users.objects.get(user_id='user123')
Tokens.deactivate_all_user_tokens(user)
```

## API Endpoints

### Logout (Single Device)
**Endpoint**: `POST /api/auth/logout/`  
**Permission**: AllowAny  
**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "logout_success": true
}
```

**Usage**:
```javascript
const response = await fetch('/api/auth/logout/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### Logout All Devices
**Endpoint**: `POST /api/auth/logout-all/`  
**Permission**: AllowAny  
**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "logout_success": true,
  "devices": "all"
}
```

**Usage**:
```javascript
const response = await fetch('/api/auth/logout-all/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

## Authentication Behavior

When a token is not ACTIVE, authentication will fail with specific error messages:

- **INACTIVE token**: `"Token is inactive"`
- **SUSPENDED token**: `"Token is suspended"`
- **Expired token**: `"Token expired"`
- **Invalid token**: `"Invalid token"`

## Use Cases

### 1. Normal Logout
User logs out from current device:
```python
# In view
token_obj = Tokens.objects.get(token=request_token)
token_obj.deactivate()
```

### 2. Logout All Devices
User wants to logout from all devices (security feature):
```python
# In view
user = request.user
Tokens.deactivate_all_user_tokens(user)
```

### 3. Temporary Suspension
Admin suspends a user's token temporarily:
```python
# Admin action
token = Tokens.objects.get(token=suspicious_token)
token.suspend()

# Later, reactivate
token.activate()
```

### 4. Security Response
Detect suspicious activity and deactivate all tokens:
```python
# Security system
if suspicious_activity_detected(user):
    Tokens.deactivate_all_user_tokens(user)
    # Force user to login again
```

## Frontend Implementation

### Logout Flow
```javascript
// Logout function
async function logout() {
  const token = localStorage.getItem('token');
  
  try {
    await fetch('/api/auth/logout/', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
  } finally {
    // Clear local storage regardless of response
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_id');
    // Redirect to login
    window.location.href = '/login';
  }
}
```

### Logout All Devices
```javascript
async function logoutAllDevices() {
  const token = localStorage.getItem('token');
  
  try {
    const response = await fetch('/api/auth/logout-all/', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (response.ok) {
      alert('Logged out from all devices');
    }
  } finally {
    localStorage.clear();
    window.location.href = '/login';
  }
}
```

### Handle Token Status Errors
```javascript
async function makeAuthenticatedRequest(url) {
  const token = localStorage.getItem('token');
  
  const response = await fetch(url, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  if (response.status === 401) {
    const error = await response.json();
    
    if (error.detail.includes('inactive') || 
        error.detail.includes('suspended')) {
      // Token was deactivated/suspended
      localStorage.clear();
      window.location.href = '/login';
    } else if (error.detail.includes('expired')) {
      // Try to refresh token
      await refreshToken();
    }
  }
  
  return response;
}
```

## Database Queries

### Get all active tokens for a user
```python
active_tokens = Tokens.objects.filter(
    user_id=user,
    token_status='ACTIVE'
)
```

### Get all inactive tokens
```python
inactive_tokens = Tokens.objects.filter(
    token_status='INACTIVE'
)
```

### Count active sessions per user
```python
from django.db.models import Count

user_sessions = Tokens.objects.filter(
    token_status='ACTIVE'
).values('user_id').annotate(
    session_count=Count('id')
)
```

## Admin Actions

### Suspend User Account
```python
# Suspend all user tokens
user = Users.objects.get(user_id='user123')
Tokens.objects.filter(
    user_id=user,
    token_status='ACTIVE'
).update(token_status='SUSPENDED')
```

### Reactivate User Account
```python
# Reactivate suspended tokens
user = Users.objects.get(user_id='user123')
Tokens.objects.filter(
    user_id=user,
    token_status='SUSPENDED'
).update(token_status='ACTIVE')
```

## Security Best Practices

1. **Always deactivate tokens on logout** - Don't just delete from client
2. **Implement logout all devices** - Give users security control
3. **Monitor token status** - Track suspicious patterns
4. **Clean up old tokens** - Periodically delete old INACTIVE tokens
5. **Log token changes** - Audit trail for security

## Cleanup Script

Periodically clean up old inactive tokens:
```python
from django.utils import timezone
from datetime import timedelta
from backend.models import Tokens

# Delete inactive tokens older than 30 days
cutoff_date = timezone.now() - timedelta(days=30)
Tokens.objects.filter(
    token_status='INACTIVE',
    issued_at__lt=cutoff_date
).delete()
```

## Testing

### Test Token Deactivation
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"identifier":"user123","password":"pass","is_admin":false}'

# Use token
curl -X GET http://localhost:8000/api/user/profile/ \
  -H "Authorization: Bearer <token>"

# Logout
curl -X POST http://localhost:8000/api/auth/logout/ \
  -H "Authorization: Bearer <token>"

# Try to use token again (should fail)
curl -X GET http://localhost:8000/api/user/profile/ \
  -H "Authorization: Bearer <token>"
```
