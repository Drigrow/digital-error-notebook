from app.extensions import db


class MistakeItem(db.Model):
    __tablename__ = "mistake_items"

    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey("notes.id"), nullable=True, index=True)
    crop_image_path = db.Column(db.String(500), nullable=True)
    correction_image_path = db.Column(db.String(500), nullable=True)
    diagram_image_path = db.Column(db.String(500), nullable=True)
    ocr_question = db.Column(db.Text, default="")
    ocr_answer = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="UNSOLVED")
    bbox_json = db.Column(db.Text, nullable=True)  # JSON string: {"x", "y", "w", "h"}
    confidence = db.Column(db.Float, default=0.0)
    needs_user_edit = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "note_id": self.note_id,
            "crop_image_path": self.crop_image_path,
            "correction_image_path": self.correction_image_path,
            "diagram_image_path": self.diagram_image_path,
            "ocr_question": self.ocr_question,
            "ocr_answer": self.ocr_answer,
            "status": self.status,
            "bbox_json": self.bbox_json,
            "confidence": self.confidence,
            "needs_user_edit": self.needs_user_edit,
        }
