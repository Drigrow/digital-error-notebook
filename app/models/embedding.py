from app.extensions import db


class Embedding(db.Model):
    __tablename__ = "embeddings"

    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey("notes.id"), nullable=False, index=True)
    chunk_text = db.Column(db.Text, nullable=False)
    vector_blob = db.Column(db.LargeBinary, nullable=False)  # numpy array as bytes
