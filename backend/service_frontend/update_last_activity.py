from django.utils import timezone
from datetime import timedelta
from backend.models import UserActivity, Tokens


def update_last_activity(user, token):
    """Update user's last activity timestamp"""
    #check if token and user are present in token table 
    token_user_exists = Tokens.objects.filter(token=token, user_id=user, token_status="ACTIVE").exists()
    if token_user_exists:
        UserActivity.objects.update_or_create(
            user_id=user,
            defaults={'last_activity': timezone.now()}
        )
        return True
    
    return False
    
    


def get_online_status(user):
    """Get user online status based on last activity"""
    try:
        activity = UserActivity.objects.get(user_id=user)
        now = timezone.now()
        diff = now - activity.last_activity
        
        if diff < timedelta(minutes=5):
            return 'online'
        elif diff < timedelta(minutes=35):
            minutes_ago = int(diff.total_seconds() / 60)
            return f'{minutes_ago} min ago'
        else:
            return 'offline'
    except UserActivity.DoesNotExist:
        return 'offline'
