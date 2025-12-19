from django.utils import timezone
from datetime import timedelta
from backend.models import UserActivity


def update_last_activity(user):
    """Update user's last activity timestamp"""
    UserActivity.objects.update_or_create(
        user_id=user,
        defaults={'last_activity': timezone.now()}
    )


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
