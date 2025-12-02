# Farmo Backend Security Implementation

## Security Measures Implemented

### 1. Password Security
- **Hashing**: All passwords stored using Django's `make_password()` with PBKDF2 algorithm
- **Validation**: Django password validators enforce strong passwords
- **Models**: Users and Credentials models have `set_password()` and `check_password()` methods
- **Never stored in plain text**

### 2. Wallet PIN Security
- **Hashing**: PINs stored as hashed strings using Django's password hasher
- **Verification**: `check_pin()` method validates without exposing raw PIN
- **API Protection**: PIN verification requires JWT authentication

### 3. JWT Authentication
- **Access Token**: 1-hour lifetime
- **Refresh Token**: 7-day lifetime with rotation
- **Algorithm**: HS256 with SECRET_KEY signing
- **Header**: Bearer token in Authorization header

### 4. API Security
- **Authentication Required**: All endpoints require JWT by default
- **CORS**: Configured for React frontend only
- **HTTPS**: SSL redirect enabled in production
- **CSRF Protection**: Enabled for state-changing operations

### 5. Data Transfer Security
- **Serializers**: Passwords/PINs marked as `write_only=True`
- **Never returned in API responses**
- **Validation on input**

### 6. HTTP Security Headers
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (HSTS) in production

## Usage

### Registration
```bash
POST /api/auth/register/
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "f_name": "John",
  "l_name": "Doe",
  "phone": "1234567890"
}
```

### Login
```bash
POST /api/auth/login/
{
  "identifier": "....",
  "password": "SecurePass123!"
}
```

### Authenticated Requests
```bash
Authorization: Bearer <access_token>
```

### Wallet PIN Verification
```bash
POST /api/wallet/verify-pin/
Authorization: Bearer <access_token>
{
  "wallet_id": "W123",
  "pin": "1234"
}
```

## Migration Required
Run: `python manage.py makemigrations && python manage.py migrate`

## Install Dependencies
Run: `pip install -r requirements.txt`
