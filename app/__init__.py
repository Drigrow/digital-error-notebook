import os
from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure directories exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "crops"), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.upload import upload_bp
    from app.routes.notes import notes_bp
    from app.routes.quiz import quiz_bp
    from app.routes.chat import chat_bp
    from app.routes.admin import admin_bp
    from app.routes.pages import pages_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(pages_bp)

    # User loader
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Create tables and seed admin on first run
    with app.app_context():
        from app.models import user, note, mistake_item, subject, tag, quiz, chat, quota, embedding  # noqa
        db.create_all()
        _seed_admin(app)

    return app


def _seed_admin(app):
    from app.models.user import User
    from app.models.quota import Quota

    admin = User.query.filter_by(username=app.config["ADMIN_USERNAME"]).first()
    if not admin:
        admin = User(
            username=app.config["ADMIN_USERNAME"],
            email="admin@localhost",
            is_admin=True,
        )
        admin.set_password(app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.flush()
        q = Quota(
            user_id=admin.id,
            remaining_chat=9999,
            remaining_images=9999,
            remaining_quizzes=9999,
            max_chat=9999,
            max_images=9999,
            max_quizzes=9999,
        )
        db.session.add(q)
        db.session.commit()
