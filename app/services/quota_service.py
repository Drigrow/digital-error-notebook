from datetime import datetime, timezone, timedelta
from app.extensions import db
from app.models.quota import Quota
from flask import current_app


def _maybe_refresh(quota):
    """Auto-refresh quota if enough time has passed."""
    now = datetime.now(timezone.utc)
    hours = quota.refresh_interval_hours or current_app.config.get("QUOTA_REFRESH_HOURS", 6)
    if quota.last_refresh is None or (now - quota.last_refresh.replace(tzinfo=timezone.utc)) >= timedelta(hours=hours):
        quota.remaining_chat = quota.max_chat
        quota.remaining_images = quota.max_images
        quota.remaining_quizzes = quota.max_quizzes
        quota.last_refresh = now
        db.session.commit()


def check_and_decrement(user_id, resource_type, count=1):
    """
    Check if user has enough quota for the resource.
    If yes, decrement and return True.
    If no, return False.

    resource_type: 'chat' | 'images' | 'quizzes'
    """
    quota = Quota.query.filter_by(user_id=user_id).first()
    if not quota:
        return False

    _maybe_refresh(quota)

    field = f"remaining_{resource_type}"
    current = getattr(quota, field, 0)
    if current < count:
        return False

    setattr(quota, field, current - count)
    db.session.commit()
    return True


def get_remaining(user_id):
    """Get current remaining quotas for a user."""
    quota = Quota.query.filter_by(user_id=user_id).first()
    if not quota:
        return {"remaining_chat": 0, "remaining_images": 0, "remaining_quizzes": 0}
    _maybe_refresh(quota)
    return quota.to_dict(hide_max=True)


def get_warnings(user_id):
    """Return warning messages for resources that are running low (≤ 3)."""
    remaining = get_remaining(user_id)
    warnings = []
    if remaining["remaining_chat"] <= 3:
        warnings.append(f"You have {remaining['remaining_chat']} chats remaining.")
    if remaining["remaining_images"] <= 3:
        warnings.append(f"You have {remaining['remaining_images']} images remaining.")
    if remaining["remaining_quizzes"] <= 3:
        warnings.append(f"You have {remaining['remaining_quizzes']} quizzes remaining.")
    return warnings
