import json
from flask import Blueprint, request, jsonify, Response, stream_with_context, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.chat import ChatThread, ChatMessage
from app.models.note import Note
from app.middleware.quota_middleware import require_quota
from app.services.openrouter import OpenRouterService
from app.services.embedding_service import retrieve_relevant_chunks

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


def _build_context_messages(thread, note_ids=None, user_message=None):
    """Build message list with optional RAG context."""
    messages = []

    # System message with note context
    system_content = "You are a helpful study assistant for a Chinese student. Help them understand their homework/exam mistakes and improve. Respond in the same language as the user's message."

    # RAG: retrieve relevant context
    if user_message:
        if note_ids:
            # User selected specific notes — restrict retrieval to those
            chunks = retrieve_relevant_chunks(user_message, current_user.id, note_ids=note_ids, top_k=8)
        else:
            # AUTO mode — search all user notes
            chunks = retrieve_relevant_chunks(user_message, current_user.id, top_k=8)

        if chunks:
            context_text = "\n\n---\n\n".join([
                f"[Note #{c['note_id']}] {c['chunk_text']}" for c in chunks
            ])
            system_content += f"\n\nRelevant study notes for context:\n{context_text}"

    messages.append({"role": "system", "content": system_content})

    # Add conversation history
    for msg in thread.messages:
        messages.append({"role": msg.role, "content": msg.content})

    return messages


@chat_bp.route("/threads", methods=["GET"])
@login_required
def list_threads():
    threads = ChatThread.query.filter_by(user_id=current_user.id).order_by(
        ChatThread.created_at.desc()
    ).all()
    return jsonify({"threads": [t.to_dict() for t in threads]})


@chat_bp.route("/threads", methods=["POST"])
@login_required
def create_thread():
    data = request.get_json() or {}
    thread = ChatThread(
        user_id=current_user.id,
        title=data.get("title", "New Chat"),
    )
    db.session.add(thread)
    db.session.commit()
    return jsonify(thread.to_dict()), 201


@chat_bp.route("/threads/<int:thread_id>", methods=["DELETE"])
@login_required
def delete_thread(thread_id):
    thread = ChatThread.query.filter_by(id=thread_id, user_id=current_user.id).first_or_404()
    db.session.delete(thread)
    db.session.commit()
    return jsonify({"message": "Thread deleted"})


@chat_bp.route("/threads/<int:thread_id>/messages", methods=["GET"])
@login_required
def get_messages(thread_id):
    thread = ChatThread.query.filter_by(id=thread_id, user_id=current_user.id).first_or_404()
    return jsonify(thread.to_dict(include_messages=True))


@chat_bp.route("/threads/<int:thread_id>/messages", methods=["POST"])
@login_required
@require_quota("chat")
def send_message(thread_id):
    thread = ChatThread.query.filter_by(id=thread_id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    content = data.get("content", "").strip()
    model = data.get("model")
    note_ids = data.get("note_ids", [])  # Selected notes for context
    stream = data.get("stream", True)

    if not content:
        return jsonify({"error": "Message content is required"}), 400

    # Validate model
    service = OpenRouterService(user=current_user)
    available = [m["id"] for m in service.get_available_models("chat")]
    if not model or model not in available:
        model = available[0] if available else current_app.config["DEFAULT_CHAT_MODEL"]

    # Save user message
    user_msg = ChatMessage(thread_id=thread.id, role="user", content=content)
    db.session.add(user_msg)
    db.session.commit()

    # Auto-title on first message
    if len(thread.messages) <= 1:
        thread.title = content[:50] + ("..." if len(content) > 50 else "")
        db.session.commit()

    # Build messages with RAG context
    messages = _build_context_messages(thread, note_ids=note_ids or None, user_message=content)

    if stream:
        def generate():
            full_response = ""
            try:
                for chunk in service.chat_completion_stream(messages, model=model):
                    full_response += chunk
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

            # Save assistant message
            if full_response:
                with current_app.app_context():
                    assistant_msg = ChatMessage(thread_id=thread.id, role="assistant", content=full_response)
                    db.session.add(assistant_msg)
                    db.session.commit()

            yield "data: [DONE]\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        # Non-streaming
        try:
            response = service.chat_completion(messages, model=model)
            assistant_msg = ChatMessage(thread_id=thread.id, role="assistant", content=response)
            db.session.add(assistant_msg)
            db.session.commit()
            return jsonify(assistant_msg.to_dict())
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@chat_bp.route("/threads/<int:thread_id>/messages/<int:msg_id>", methods=["PUT"])
@login_required
def edit_message(thread_id, msg_id):
    """Edit the last user message — deletes messages after it."""
    thread = ChatThread.query.filter_by(id=thread_id, user_id=current_user.id).first_or_404()
    msg = ChatMessage.query.filter_by(id=msg_id, thread_id=thread.id, role="user").first_or_404()

    data = request.get_json()
    new_content = data.get("content", "").strip()
    if not new_content:
        return jsonify({"error": "Content required"}), 400

    # Delete all messages after this one
    ChatMessage.query.filter(
        ChatMessage.thread_id == thread.id,
        ChatMessage.created_at > msg.created_at
    ).delete()

    msg.content = new_content
    db.session.commit()

    return jsonify({"message": "Message updated", "msg": msg.to_dict()})


@chat_bp.route("/threads/<int:thread_id>/regenerate", methods=["POST"])
@login_required
@require_quota("chat")
def regenerate_response(thread_id):
    """Delete last assistant message and regenerate."""
    thread = ChatThread.query.filter_by(id=thread_id, user_id=current_user.id).first_or_404()

    # Find and delete last assistant message
    last_assistant = ChatMessage.query.filter_by(
        thread_id=thread.id, role="assistant"
    ).order_by(ChatMessage.created_at.desc()).first()

    if last_assistant:
        db.session.delete(last_assistant)
        db.session.commit()

    # Get last user message for context
    last_user = ChatMessage.query.filter_by(
        thread_id=thread.id, role="user"
    ).order_by(ChatMessage.created_at.desc()).first()

    data = request.get_json() or {}
    model = data.get("model")
    note_ids = data.get("note_ids", [])

    service = OpenRouterService(user=current_user)
    available = [m["id"] for m in service.get_available_models("chat")]
    if not model or model not in available:
        model = available[0] if available else current_app.config["DEFAULT_CHAT_MODEL"]

    messages = _build_context_messages(
        thread,
        note_ids=note_ids or None,
        user_message=last_user.content if last_user else ""
    )

    def generate():
        full_response = ""
        try:
            for chunk in service.chat_completion_stream(messages, model=model):
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        if full_response:
            with current_app.app_context():
                assistant_msg = ChatMessage(thread_id=thread.id, role="assistant", content=full_response)
                db.session.add(assistant_msg)
                db.session.commit()

        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
