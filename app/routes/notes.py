import json
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.note import Note, note_tags
from app.models.mistake_item import MistakeItem
from app.models.subject import Subject
from app.models.tag import Tag
from app.services.embedding_service import store_embeddings_for_note

notes_bp = Blueprint("notes", __name__, url_prefix="/api")


@notes_bp.route("/notes", methods=["GET"])
@login_required
def list_notes():
    query = Note.query.filter_by(user_id=current_user.id)

    # Filters
    subject_id = request.args.get("subject_id")
    if subject_id:
        query = query.filter_by(subject_id=int(subject_id))

    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status.upper())

    tag_ids = request.args.getlist("tag_ids")
    if tag_ids:
        for tid in tag_ids:
            query = query.filter(Note.tags.any(Tag.id == int(tid)))

    date_from = request.args.get("date_from")
    if date_from:
        query = query.filter(Note.created_at >= datetime.fromisoformat(date_from))

    date_to = request.args.get("date_to")
    if date_to:
        query = query.filter(Note.created_at <= datetime.fromisoformat(date_to))

    search = request.args.get("q")
    if search:
        query = query.filter(
            db.or_(
                Note.title.ilike(f"%{search}%"),
                Note.content_md.ilike(f"%{search}%"),
            )
        )

    query = query.order_by(Note.updated_at.desc())

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "notes": [n.to_dict() for n in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    })


@notes_bp.route("/notes", methods=["POST"])
@login_required
def create_note():
    data = request.get_json()

    # Get or create subject
    subject_id = None
    subject_name = data.get("subject", "").strip()
    if subject_name:
        subject = Subject.query.filter_by(name=subject_name, user_id=current_user.id).first()
        if not subject:
            subject = Subject(name=subject_name, user_id=current_user.id)
            db.session.add(subject)
            db.session.flush()
        subject_id = subject.id

    # Create note
    note = Note(
        user_id=current_user.id,
        subject_id=subject_id,
        title=data.get("title", "Untitled"),
        content_md=data.get("content_md", ""),
        status=data.get("status", "UNSOLVED"),
    )
    db.session.add(note)
    db.session.flush()

    # Get or create tags
    tag_names = data.get("tags", [])
    for tname in tag_names:
        tname = tname.strip()
        if not tname:
            continue
        tag = Tag.query.filter_by(name=tname, user_id=current_user.id).first()
        if not tag:
            tag = Tag(name=tname, user_id=current_user.id)
            db.session.add(tag)
            db.session.flush()
        note.tags.append(tag)

    # Create mistake items
    mistake_items = data.get("mistake_items", [])
    for mi_data in mistake_items:
        mi = MistakeItem(
            note_id=note.id,
            crop_image_path=mi_data.get("crop_image_path"),
            correction_image_path=mi_data.get("correction_image_path"),
            diagram_image_path=mi_data.get("diagram_image_path"),
            ocr_question=mi_data.get("ocr_question", ""),
            ocr_answer=mi_data.get("ocr_answer"),
            status=mi_data.get("status", "UNSOLVED"),
            bbox_json=mi_data.get("bbox_json"),
            confidence=mi_data.get("confidence", 0.0),
            needs_user_edit=mi_data.get("needs_user_edit", False),
        )
        db.session.add(mi)

    db.session.commit()

    # Generate embeddings
    try:
        store_embeddings_for_note(note)
    except Exception:
        pass  # Non-critical

    return jsonify(note.to_dict()), 201


@notes_bp.route("/notes/<int:note_id>", methods=["GET"])
@login_required
def get_note(note_id):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    return jsonify(note.to_dict())


@notes_bp.route("/notes/<int:note_id>", methods=["PUT"])
@login_required
def update_note(note_id):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    data = request.get_json()

    if "title" in data:
        note.title = data["title"]
    if "content_md" in data:
        note.content_md = data["content_md"]
    if "status" in data:
        note.status = data["status"]

    # Update subject
    if "subject" in data:
        subject_name = data["subject"].strip()
        if subject_name:
            subject = Subject.query.filter_by(name=subject_name, user_id=current_user.id).first()
            if not subject:
                subject = Subject(name=subject_name, user_id=current_user.id)
                db.session.add(subject)
                db.session.flush()
            note.subject_id = subject.id
        else:
            note.subject_id = None

    # Update tags
    if "tags" in data:
        note.tags.clear()
        for tname in data["tags"]:
            tname = tname.strip()
            if not tname:
                continue
            tag = Tag.query.filter_by(name=tname, user_id=current_user.id).first()
            if not tag:
                tag = Tag(name=tname, user_id=current_user.id)
                db.session.add(tag)
                db.session.flush()
            note.tags.append(tag)

    note.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    # Refresh embeddings
    try:
        store_embeddings_for_note(note)
    except Exception:
        pass

    return jsonify(note.to_dict())


@notes_bp.route("/notes/<int:note_id>", methods=["DELETE"])
@login_required
def delete_note(note_id):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    db.session.delete(note)
    db.session.commit()
    return jsonify({"message": "Note deleted"})


@notes_bp.route("/subjects", methods=["GET"])
@login_required
def list_subjects():
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    return jsonify({"subjects": [s.to_dict() for s in subjects]})


@notes_bp.route("/tags", methods=["GET"])
@login_required
def list_tags():
    tags = Tag.query.filter_by(user_id=current_user.id).all()
    return jsonify({"tags": [t.to_dict() for t in tags]})
