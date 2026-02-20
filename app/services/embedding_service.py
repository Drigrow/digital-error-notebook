import numpy as np
from flask import current_app
from app.extensions import db
from app.models.embedding import Embedding
from app.services.openrouter import OpenRouterService


def _simple_text_to_vector(text, dim=384):
    """
    Simple bag-of-characters embedding for lightweight similarity search.
    For production, replace with a proper embedding model call.
    Uses character n-gram hashing to create a fixed-size vector.
    """
    vec = np.zeros(dim, dtype=np.float32)
    text = text.lower().strip()
    if not text:
        return vec

    # Character trigram hashing
    for i in range(len(text) - 2):
        trigram = text[i:i+3]
        h = hash(trigram) % dim
        vec[h] += 1.0

    # Word-level hashing
    words = text.split()
    for word in words:
        h = hash(word) % dim
        vec[h] += 2.0  # Weight words more than char trigrams

    # Normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    return vec


def generate_embedding(text):
    """Generate an embedding vector for the given text."""
    return _simple_text_to_vector(text)


def store_embeddings_for_note(note):
    """
    Generate and store embeddings for a note's content and mistake items.
    Chunks the content into manageable pieces.
    """
    # Remove old embeddings for this note
    Embedding.query.filter_by(note_id=note.id).delete()

    chunks = []

    # Chunk the markdown content
    if note.content_md:
        content = note.content_md.strip()
        # Split by paragraphs / sections
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        for para in paragraphs:
            if len(para) > 20:  # Skip very short chunks
                chunks.append(para)

    # Add mistake item OCR text
    for item in note.mistake_items:
        if item.ocr_question:
            chunks.append(f"Question: {item.ocr_question}")
        if item.ocr_answer:
            chunks.append(f"Answer: {item.ocr_answer}")

    # Add title + subject + tags as a chunk
    meta_parts = [note.title]
    if note.subject:
        meta_parts.append(note.subject.name)
    meta_parts.extend([t.name for t in note.tags])
    meta_chunk = " ".join(meta_parts)
    if meta_chunk.strip():
        chunks.append(meta_chunk)

    # Generate and store embeddings
    for chunk_text in chunks:
        vec = generate_embedding(chunk_text)
        emb = Embedding(
            note_id=note.id,
            chunk_text=chunk_text,
            vector_blob=vec.tobytes(),
        )
        db.session.add(emb)

    db.session.commit()


def retrieve_relevant_chunks(query, user_id, note_ids=None, top_k=8):
    """
    Retrieve the most relevant chunks for a query using cosine similarity.

    Args:
        query: search query text
        user_id: restrict to this user's notes
        note_ids: if provided, restrict to these specific note IDs
        top_k: number of results to return

    Returns:
        list of dicts with chunk_text, note_id, similarity
    """
    from app.models.note import Note

    query_vec = generate_embedding(query)

    # Build query for embeddings
    emb_query = db.session.query(Embedding).join(Note).filter(Note.user_id == user_id)
    if note_ids:
        emb_query = emb_query.filter(Embedding.note_id.in_(note_ids))

    embeddings = emb_query.all()
    if not embeddings:
        return []

    # Compute similarities
    results = []
    for emb in embeddings:
        stored_vec = np.frombuffer(emb.vector_blob, dtype=np.float32)
        sim = float(np.dot(query_vec, stored_vec))
        results.append({
            "chunk_text": emb.chunk_text,
            "note_id": emb.note_id,
            "similarity": sim,
        })

    # Sort by similarity descending, return top-k
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]
