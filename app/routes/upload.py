import os
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.middleware.quota_middleware import require_quota
from app.services.vision_pipeline import run_vision_pipeline, suggest_subject_and_tags
from app.utils.image_utils import save_upload
from app.services.openrouter import OpenRouterService

upload_bp = Blueprint("upload", __name__, url_prefix="/api")


@upload_bp.route("/upload", methods=["POST"])
@login_required
def upload_images():
    files = request.files.getlist("images")
    if not files:
        return jsonify({"error": "No images uploaded"}), 400

    # Check image quota
    image_count = len(files)
    from app.services.quota_service import check_and_decrement
    if not current_user.is_admin:
        if not check_and_decrement(current_user.id, "images", image_count):
            return jsonify({"error": "Image quota exhausted. Please wait for quota refresh."}), 429

    model = request.form.get("model", current_app.config["DEFAULT_VISION_MODEL"])

    # Validate model access
    service = OpenRouterService(user=current_user)
    available = [m["id"] for m in service.get_available_models("vision")]
    if model not in available:
        model = available[0] if available else current_app.config["DEFAULT_VISION_MODEL"]

    upload_folder = current_app.config["UPLOAD_FOLDER"]

    # Save uploaded files
    saved_paths = []
    for f in files:
        if f.filename:
            filename = save_upload(f, upload_folder)
            saved_paths.append(filename)

    if not saved_paths:
        return jsonify({"error": "No valid images uploaded"}), 400

    # Run vision pipeline
    result = run_vision_pipeline(saved_paths, model, current_user)

    if "error" in result and not result.get("mistakes"):
        return jsonify(result), 500

    # Suggest subject and tags
    if result.get("mistakes"):
        suggestions = suggest_subject_and_tags(result["mistakes"], current_user)
        result["suggested_subject"] = suggestions.get("subject", "")
        result["suggested_tags"] = suggestions.get("tags", [])

    return jsonify(result)


@upload_bp.route("/models/vision", methods=["GET"])
@login_required
def get_vision_models():
    service = OpenRouterService(user=current_user)
    return jsonify({"models": service.get_available_models("vision")})


@upload_bp.route("/models/chat", methods=["GET"])
@login_required
def get_chat_models():
    service = OpenRouterService(user=current_user)
    return jsonify({"models": service.get_available_models("chat")})
