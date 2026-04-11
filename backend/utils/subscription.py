from datetime import datetime
from backend.models import db

def is_premium_active(user):
    """Check if user has an active premium subscription."""
    if not user.is_premium:
        return False
    if user.subscription_expiry and user.subscription_expiry < datetime.utcnow():
        user.is_premium = False
        db.session.commit()
        return False
    return True
