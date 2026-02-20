from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.quota import Quota
from app.middleware.quota_middleware import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/users", methods=["GET"])
@login_required
@admin_required
def list_users():
    users = User.query.all()
    result = []
    for u in users:
        quota = Quota.query.filter_by(user_id=u.id).first()
        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_admin": u.is_admin,
            "has_api_key": u.has_own_api_key(),
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "quota": quota.to_dict(hide_max=False) if quota else None,
        })
    return jsonify({"users": result})


@admin_bp.route("/users/<int:user_id>/quota", methods=["PUT"])
@login_required
@admin_required
def update_quota(user_id):
    user = User.query.get_or_404(user_id)
    quota = Quota.query.filter_by(user_id=user.id).first()
    if not quota:
        quota = Quota(user_id=user.id)
        db.session.add(quota)

    data = request.get_json()
    if "max_chat" in data:
        quota.max_chat = data["max_chat"]
    if "max_images" in data:
        quota.max_images = data["max_images"]
    if "max_quizzes" in data:
        quota.max_quizzes = data["max_quizzes"]
    if "remaining_chat" in data:
        quota.remaining_chat = data["remaining_chat"]
    if "remaining_images" in data:
        quota.remaining_images = data["remaining_images"]
    if "remaining_quizzes" in data:
        quota.remaining_quizzes = data["remaining_quizzes"]
    if "refresh_interval_hours" in data:
        quota.refresh_interval_hours = data["refresh_interval_hours"]

    db.session.commit()
    return jsonify({"message": "Quota updated", "quota": quota.to_dict(hide_max=False)})
