from datetime import datetime, timezone
from app.extensions import db

# Many-to-many association table for notes ↔ tags
note_tags = db.Table(
    "note_tags",
    db.Column("note_id", db.Integer, db.ForeignKey("notes.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)
    title = db.Column(db.String(200), nullable=False, default="Untitled")
    content_md = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="UNSOLVED")  # SOLVED / UNSOLVED
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    mistake_items = db.relationship("MistakeItem", backref="note", lazy="select", cascade="all, delete-orphan")
    tags = db.relationship("Tag", secondary=note_tags, backref=db.backref("notes", lazy="dynamic"))
    subject = db.relationship("Subject", backref=db.backref("notes", lazy="dynamic"))
    embeddings = db.relationship("Embedding", backref="note", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content_md": self.content_md,
            "status": self.status,
            "subject": self.subject.name if self.subject else None,
            "subject_id": self.subject_id,
            "tags": [t.name for t in self.tags],
            "tag_ids": [t.id for t in self.tags],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "mistake_items": [m.to_dict() for m in self.mistake_items],
        }
