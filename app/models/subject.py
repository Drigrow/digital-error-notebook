from app.extensions import db


class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    __table_args__ = (db.UniqueConstraint("name", "user_id", name="uq_subject_user"),)

    def to_dict(self):
        return {"id": self.id, "name": self.name}
