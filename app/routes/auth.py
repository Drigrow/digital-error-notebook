from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.quota import Quota
from app.utils.crypto import encrypt_api_key
from app.services.quota_service import get_remaining, get_warnings
from flask import current_app

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    # Create default quota
    quota = Quota(
        user_id=user.id,
        remaining_chat=current_app.config.get("DEFAULT_QUOTA_CHAT", 50),
        remaining_images=current_app.config.get("DEFAULT_QUOTA_IMAGES", 20),
        remaining_quizzes=current_app.config.get("DEFAULT_QUOTA_QUIZZES", 10),
        max_chat=current_app.config.get("DEFAULT_QUOTA_CHAT", 50),
        max_images=current_app.config.get("DEFAULT_QUOTA_IMAGES", 20),
        max_quizzes=current_app.config.get("DEFAULT_QUOTA_QUIZZES", 10),
    )
    db.session.add(quota)
    db.session.commit()

    login_user(user)
    return jsonify({"message": "Registration successful", "user": {"id": user.id, "username": user.username}}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    login_user(user, remember=True)
    return jsonify({
        "message": "Login successful",
        "user": {"id": user.id, "username": user.username, "is_admin": user.is_admin}
    })


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out"})


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    remaining = get_remaining(current_user.id)
    warnings = get_warnings(current_user.id)
    return jsonify({
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "is_admin": current_user.is_admin,
            "has_api_key": current_user.has_own_api_key(),
        },
        "quota": remaining,
        "warnings": warnings,
    })


@auth_bp.route("/api-key", methods=["PUT"])
@login_required
def update_api_key():
    data = request.get_json()
    key = data.get("api_key", "").strip()

    if key:
        current_user.openrouter_api_key_enc = encrypt_api_key(key)
    else:
        current_user.openrouter_api_key_enc = None

    db.session.commit()
    return jsonify({"message": "API key updated", "has_api_key": current_user.has_own_api_key()})
