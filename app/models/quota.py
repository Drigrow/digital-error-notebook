from datetime import datetime, timezone
from app.extensions import db


class Quota(db.Model):
    __tablename__ = "quotas"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    remaining_chat = db.Column(db.Integer, default=50)
    remaining_images = db.Column(db.Integer, default=20)
    remaining_quizzes = db.Column(db.Integer, default=10)
    max_chat = db.Column(db.Integer, default=50)
    max_images = db.Column(db.Integer, default=20)
    max_quizzes = db.Column(db.Integer, default=10)
    refresh_interval_hours = db.Column(db.Integer, default=6)
    last_refresh = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self, hide_max=True):
        d = {
            "remaining_chat": self.remaining_chat,
            "remaining_images": self.remaining_images,
            "remaining_quizzes": self.remaining_quizzes,
        }
        if not hide_max:
            d.update({
                "max_chat": self.max_chat,
                "max_images": self.max_images,
                "max_quizzes": self.max_quizzes,
                "refresh_interval_hours": self.refresh_interval_hours,
            })
        return d
