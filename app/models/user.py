from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    openrouter_api_key_enc = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    notes = db.relationship("Note", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    subjects = db.relationship("Subject", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    tags = db.relationship("Tag", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    quiz_sessions = db.relationship("QuizSession", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    chat_threads = db.relationship("ChatThread", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    quota = db.relationship("Quota", backref="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_own_api_key(self):
        return self.openrouter_api_key_enc is not None and self.openrouter_api_key_enc != ""

    def __repr__(self):
        return f"<User {self.username}>"
