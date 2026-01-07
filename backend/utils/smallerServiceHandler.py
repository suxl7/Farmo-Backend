def get_half_email(email: str) -> str:
    # Split into local part and domain
    local, domain = email.split("@")
    
    # Keep first 3 and last 2 characters of local part
    if len(local) > 5:
        masked_local = local[:3] + "*****" + local[-2:]
    else:
        # For very short local parts, just mask the middle
        masked_local = local[0] + "*****" + local[-1]
    
    return masked_local + "@" + domain