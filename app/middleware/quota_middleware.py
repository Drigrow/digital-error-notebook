from functools import wraps
from flask import jsonify
from flask_login import current_user
from app.services.quota_service import check_and_decrement


def require_quota(resource_type, count=1):
    """Decorator to enforce quota before an endpoint executes."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Login required"}), 401
            if current_user.is_admin:
                return f(*args, **kwargs)  # Admin bypasses quota
            if not check_and_decrement(current_user.id, resource_type, count):
                return jsonify({
                    "error": f"Quota exhausted for {resource_type}. Please wait for your quota to refresh."
                }), 429
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Decorator to restrict access to admin users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function
