from datetime import datetime, timezone
from app.extensions import db


class QuizSession(db.Model):
    __tablename__ = "quiz_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    mode = db.Column(db.String(30), nullable=False)  # "original" or "generated"
    filters_json = db.Column(db.Text, nullable=True)  # JSON: subject, tags, date range, status
    score = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    questions = db.relationship("QuizQuestion", backref="session", lazy="select", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "mode": self.mode,
            "filters_json": self.filters_json,
            "score": self.score,
            "total": self.total,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "questions": [q.to_dict() for q in self.questions],
        }


class QuizQuestion(db.Model):
    __tablename__ = "quiz_questions"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("quiz_sessions.id"), nullable=False)
    note_id = db.Column(db.Integer, db.ForeignKey("notes.id"), nullable=True)
    question_text = db.Column(db.Text, nullable=False)
    question_image_path = db.Column(db.String(500), nullable=True)
    reference_answer = db.Column(db.Text, nullable=True)
    user_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "note_id": self.note_id,
            "question_text": self.question_text,
            "question_image_path": self.question_image_path,
            "reference_answer": self.reference_answer,
            "user_answer": self.user_answer,
            "is_correct": self.is_correct,
        }
