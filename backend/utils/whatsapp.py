import re

def normalize_whatsapp(value):
    # Pattern for wa.me link
    wa_link_pattern = r"^https?://wa\.me/\+97798\d{7}$"
    # Pattern for direct Nepali number starting with 98
    phone_pattern = r"^98\d{8}$"

    if re.match(wa_link_pattern, value):
        # Already in correct wa.me format
        return value
    elif re.match(phone_pattern, value):
        # Convert plain number to wa.me link
        return f"https://wa.me/+977{value}"
    else:
        # Invalid format
        return None
