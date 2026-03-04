# your_app/validators.py
from django.core.exceptions import ValidationError
import re

def validate_nepali_phone(value):
    """Validate Nepali phone number (exactly 10 digits starting with 9)."""
    if not value:
        return
    
    # Remove spaces, dashes, plus signs
    #phone = re.sub(r'[\s\-\+]', '', value)
    
    # Must be exactly 10 digits and start with 9
    if not re.fullmatch(r'9\d{9}', value):
        raise ValidationError(
            'Phone number must be exactly 10 digits starting with 9 (e.g., 9841234567).'
        )


def validate_email_format(value):
    """Validate email format"""
    if not value:
        return
    
    # Basic email pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, value):
        raise ValidationError('Enter a valid email address.')
    
    # Check for common typos
    if value.endswith('.con') or value.endswith('.cmo'):
        raise ValidationError('Did you mean .com?')

def validate_facebook_url(value):
    """Validate Facebook profile URL"""
    if not value:
        return
    
    # Facebook URL patterns
    valid_patterns = [
        r'^https?://(www\.)?facebook\.com/[a-zA-Z0-9.]+/?$',
        r'^https?://(www\.)?fb\.com/[a-zA-Z0-9.]+/?$',
        r'^[a-zA-Z0-9.]+$'  # Just username
    ]
    
    is_valid = any(re.match(pattern, value) for pattern in valid_patterns)
    
    if not is_valid:
        raise ValidationError(
            'Enter a valid Facebook URL (e.g., https://facebook.com/username or just username).'
        )

def validate_name(value, field_name="Name"):
    """Validate name fields (first, middle, last name)"""
    if not value:
        return
    
    # Remove extra spaces
    name = value.strip()
    
    # Check minimum length
    if len(name) < 2:
        raise ValidationError(f'{field_name} must be at least 2 characters long.')
    
    # Check maximum length
    if len(name) > 50:
        raise ValidationError(f'{field_name} must be less than 50 characters.')
    
    # Allow only letters, spaces, hyphens, and apostrophes
    # This supports names like "Mary-Jane" or "O'Brien"
    if not re.match(r"^[a-zA-Z\s\-']+$", name):
        raise ValidationError(
            f'{field_name} can only contain letters, spaces, hyphens, and apostrophes.'
        )
    
    # Check for consecutive spaces
    if '  ' in name:
        raise ValidationError(f'{field_name} cannot have consecutive spaces.')
    
    # Check if it starts/ends with space or special char
    if not name[0].isalpha() or not name[-1].isalpha():
        raise ValidationError(f'{field_name} must start and end with a letter.')

def validate_first_name(value):
    validate_name(value, "First name")

def validate_middle_name(value):
    if value:  # Middle name is optional
        validate_name(value, "Middle name")

def validate_last_name(value):
    validate_name(value, "Last name")

def validate_whatsapp(value):
    """
    Validate WhatsApp number (Nepal only: starts with 97 or 98, or wa.me link).
    Normalize plain numbers into wa.me link.
    """
    if not value:
        return None

    # Pattern for wa.me link (Nepal numbers starting with 97 or 98)
    wa_link_pattern = r"^https?://wa\.me/\+9779[78]\d{7}$"
    # Pattern for direct Nepali number starting with 97 or 98 (10 digits)
    phone_pattern = r"^9[78]\d{8}$"

    if re.match(wa_link_pattern, value):
        return
    elif re.match(phone_pattern, value):
        return
    else:
        raise ValidationError("WhatsApp must be a valid number (starting with 97 or 98) or wa.me link.")


def validate_password(password):
        
        if not password:
           return None
        # Check minimum length
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

        # Check for at least one digit
        if not re.search(r"\d", password):
            raise ValidationError("Password must contain at least one number.")

        # Check for at least one symbol (non-alphanumeric)
        if not re.search(r"[^A-Za-z0-9]", password):
            raise ValidationError("Password must contain at least one symbol.")
        
        return




