# your_app/validators.py
from django.core.exceptions import ValidationError
import re

def validate_nepali_phone(value):
    """Validate Nepali phone number (10 digits starting with 9)"""
    if not value:
        return
    
    # Remove spaces, dashes, plus signs
    phone = re.sub(r'[\s\-\+]', '', value)
    
    # Check if it's 10 digits and starts with 9
    if not re.match(r'^9\d{9}$', phone):
        raise ValidationError(
            'Phone number must be 10 digits starting with 9 (e.g., 9841234567).'
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
    """Validate WhatsApp number (can be international)"""
    if not value:
        return
    
    # Remove spaces, dashes, plus signs
    phone = re.sub(r'[\s\-\+]', '', value)
    
    # Check if it's between 10-15 digits
    if not re.match(r'^\d{10,15}$', phone):
        raise ValidationError(
            'WhatsApp number must be 10-15 digits.'
        )