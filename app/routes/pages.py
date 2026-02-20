import os
from flask import Blueprint, render_template, send_from_directory, current_app
from flask_login import login_required, current_user

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    if current_user.is_authenticated:
        return render_template("notebook.html")
    return render_template("auth/login.html")


@pages_bp.route("/login")
def login_page():
    return render_template("auth/login.html")


@pages_bp.route("/register")
def register_page():
    return render_template("auth/register.html")


@pages_bp.route("/upload")
@login_required
def upload_page():
    return render_template("upload.html")


@pages_bp.route("/review")
@login_required
def review_page():
    return render_template("review.html")


@pages_bp.route("/notebook")
@login_required
def notebook_page():
    return render_template("notebook.html")


@pages_bp.route("/note/<int:note_id>")
@login_required
def note_detail_page(note_id):
    return render_template("note_detail.html", note_id=note_id)


@pages_bp.route("/quiz")
@login_required
def quiz_page():
    return render_template("quiz.html")


@pages_bp.route("/chat")
@login_required
def chat_page():
    return render_template("chat.html")


@pages_bp.route("/profile")
@login_required
def profile_page():
    return render_template("profile.html")


@pages_bp.route("/admin")
@login_required
def admin_page():
    if not current_user.is_admin:
        return render_template("auth/login.html")
    return render_template("admin/dashboard.html")


@pages_bp.route("/uploads/<path:filename>")
@login_required
def serve_upload(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
