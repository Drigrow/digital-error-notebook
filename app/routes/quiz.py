import json
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.quiz import QuizSession, QuizQuestion
from app.models.note import Note
from app.models.tag import Tag
from app.middleware.quota_middleware import require_quota
from app.services.openrouter import OpenRouterService
from datetime import datetime

quiz_bp = Blueprint("quiz", __name__, url_prefix="/api/quiz")


def _get_filtered_notes(filters):
    """Get notes matching the provided filters."""
    query = Note.query.filter_by(user_id=current_user.id)

    if filters.get("subject_id"):
        query = query.filter_by(subject_id=int(filters["subject_id"]))
    if filters.get("status"):
        query = query.filter_by(status=filters["status"].upper())
    if filters.get("tag_ids"):
        for tid in filters["tag_ids"]:
            query = query.filter(Note.tags.any(Tag.id == int(tid)))
    if filters.get("date_from"):
        query = query.filter(Note.created_at >= datetime.fromisoformat(filters["date_from"]))
    if filters.get("date_to"):
        query = query.filter(Note.created_at <= datetime.fromisoformat(filters["date_to"]))

    return query.all()


@quiz_bp.route("/start", methods=["POST"])
@login_required
@require_quota("quizzes")
def start_quiz():
    data = request.get_json()
    mode = data.get("mode", "original")  # "original" or "generated"
    filters = data.get("filters", {})
    count = data.get("count", 5)

    notes = _get_filtered_notes(filters)
    if not notes:
        return jsonify({"error": "No notes match the selected filters"}), 404

    # Create quiz session
    session = QuizSession(
        user_id=current_user.id,
        mode=mode,
        filters_json=json.dumps(filters),
        total=min(count, len(notes)),
    )
    db.session.add(session)
    db.session.flush()

    # Select notes for quiz (limit to count)
    import random
    selected_notes = random.sample(notes, min(count, len(notes)))

    if mode == "original":
        # Use original question text and images
        for note in selected_notes:
            for mi in note.mistake_items:
                q = QuizQuestion(
                    session_id=session.id,
                    note_id=note.id,
                    question_text=mi.ocr_question or "Review this mistake",
                    question_image_path=mi.crop_image_path,
                    reference_answer=mi.ocr_answer or mi.ocr_question,
                )
                db.session.add(q)
                session.total = QuizQuestion.query.filter_by(session_id=session.id).count()
    else:
        # Generate new questions using LLM
        service = OpenRouterService(user=current_user)
        context = []
        for note in selected_notes:
            for mi in note.mistake_items:
                context.append({
                    "question": mi.ocr_question,
                    "answer": mi.ocr_answer,
                    "subject": note.subject.name if note.subject else "Unknown",
                })

        prompt = f"""Based on these homework mistakes from a Chinese student, generate {min(count, len(context))} NEW practice questions that test similar concepts. Make the questions different but related.

Original mistakes:
{json.dumps(context, ensure_ascii=False)}

RESPOND WITH VALID JSON ONLY:
{{
  "questions": [
    {{"question": "...", "reference_answer": "...", "source_index": 0}}
  ]
}}
"""
        try:
            messages = [{"role": "user", "content": prompt}]
            response = service.chat_completion(messages, temperature=0.7, max_tokens=4096)
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])
            gen_data = json.loads(response)

            for gq in gen_data.get("questions", []):
                src_idx = gq.get("source_index", 0)
                note_id = selected_notes[min(src_idx, len(selected_notes)-1)].id
                q = QuizQuestion(
                    session_id=session.id,
                    note_id=note_id,
                    question_text=gq.get("question", ""),
                    reference_answer=gq.get("reference_answer", ""),
                )
                db.session.add(q)
            session.total = len(gen_data.get("questions", []))
        except Exception as e:
            current_app.logger.error(f"Quiz generation failed: {e}")
            return jsonify({"error": f"Failed to generate quiz: {str(e)}"}), 500

    db.session.commit()
    return jsonify(session.to_dict()), 201


@quiz_bp.route("/<int:session_id>/answer", methods=["POST"])
@login_required
def submit_answer(session_id):
    session = QuizSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    question_id = data.get("question_id")
    user_answer = data.get("answer", "")

    question = QuizQuestion.query.filter_by(id=question_id, session_id=session.id).first_or_404()
    question.user_answer = user_answer

    # Simple correctness check — let the LLM judge
    service = OpenRouterService(user=current_user)
    prompt = f"""Judge whether the student's answer is correct.

Question: {question.question_text}
Reference answer: {question.reference_answer or 'Not available'}
Student answer: {user_answer}

RESPOND WITH VALID JSON ONLY:
{{"is_correct": true/false, "explanation": "..."}}
"""
    try:
        messages = [{"role": "user", "content": prompt}]
        response = service.chat_completion(messages, temperature=0.1, max_tokens=500)
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1])
        result = json.loads(response)
        question.is_correct = result.get("is_correct", False)
        if question.is_correct:
            session.score += 1
        explanation = result.get("explanation", "")
    except Exception:
        question.is_correct = None
        explanation = "Could not auto-grade. Please review."

    db.session.commit()
    return jsonify({
        "is_correct": question.is_correct,
        "explanation": explanation,
        "score": session.score,
        "total": session.total,
    })


@quiz_bp.route("/sessions", methods=["GET"])
@login_required
def list_sessions():
    sessions = QuizSession.query.filter_by(user_id=current_user.id).order_by(
        QuizSession.created_at.desc()
    ).limit(50).all()
    return jsonify({"sessions": [s.to_dict() for s in sessions]})


@quiz_bp.route("/<int:session_id>", methods=["GET"])
@login_required
def get_session(session_id):
    session = QuizSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    return jsonify(session.to_dict())
