import re

def is_phone(data: str) -> bool:
    # Regex for phone (basic: digits, optional +, spaces, dashes)
    phone_pattern = r'^\+?\d[\d\s-]{7,}$'
    return bool(re.match(phone_pattern, data))
    

def is_email(data: str) -> bool:
    # Regex for email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, data))

def is_name(data: str) -> bool:
    # Regex for name
    name_pattern = r'^[a-zA-Z\s]+$'
    return bool(re.match(name_pattern, data))

def is_password(data: str) -> bool:
    # Regex for password
    password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$'
    return bool(re.match(password_pattern, data))

