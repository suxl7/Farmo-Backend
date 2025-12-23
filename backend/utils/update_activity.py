from django.utils import timezone
from backend.models import UserActivity, Tokens

def update_activity(user, activity, discription):
    """Update user's last activity timestamp"""
    #check if token and user are present in token table 
    #token_user_exists = Tokens.objects.filter(token=token, user_id=user, token_status="ACTIVE").exists()
    #if token_user_exists:
    UserActivity.objects.create(
        user_id=user,
        activity_type=activity,
        description=discription,
        timestamp=timezone.now()
    )