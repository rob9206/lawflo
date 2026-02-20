"""AI tutor session routes with SSE streaming."""

from flask import Blueprint, request, jsonify, Response

from api.errors import ValidationError, NotFoundError
from api.services import tutor_engine
from api.services.prompt_library import MODES

bp = Blueprint("tutor", __name__, url_prefix="/api/tutor")


@bp.route("/modes", methods=["GET"])
def list_modes():
    """List available tutor modes."""
    mode_info = {
        "socratic": {"name": "Socratic Questioning", "description": "Learn through guided questions that probe your understanding"},
        "irac": {"name": "IRAC Practice", "description": "Practice structured legal analysis: Issue, Rule, Application, Conclusion"},
        "issue_spot": {"name": "Issue Spotting", "description": "Train to identify all legal issues in complex fact patterns"},
        "hypo": {"name": "Hypothetical Drill", "description": "Test rule boundaries by modifying facts and analyzing changes"},
        "explain": {"name": "Explain (Catch Up)", "description": "Compressed, high-signal teaching for rapid concept mastery"},
        "exam_strategy": {"name": "Exam Strategy", "description": "Master exam technique, time management, and answer structure"},
    }
    return jsonify(mode_info)


@bp.route("/session", methods=["POST"])
def create_session():
    """Start a new tutoring session."""
    data = request.get_json()
    if not data:
        raise ValidationError("JSON body required")

    mode = data.get("mode", "explain")
    if mode not in MODES:
        raise ValidationError(f"Invalid mode. Available: {', '.join(MODES.keys())}")

    session = tutor_engine.create_session(
        mode=mode,
        subject=data.get("subject"),
        topics=data.get("topics"),
    )
    return jsonify(session), 201


@bp.route("/session/<session_id>", methods=["GET"])
def get_session(session_id: str):
    """Get session details with message history."""
    session = tutor_engine.get_session(session_id)
    if not session:
        raise NotFoundError("Session not found")
    return jsonify(session)


@bp.route("/message", methods=["POST"])
def send_message():
    """Send a message and stream Claude's response via SSE."""
    data = request.get_json()
    if not data:
        raise ValidationError("JSON body required")

    session_id = data.get("session_id")
    content = data.get("content")

    if not session_id or not content:
        raise ValidationError("session_id and content are required")

    def generate():
        try:
            for chunk in tutor_engine.send_message(session_id, content):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except ValueError as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@bp.route("/session/<session_id>/end", methods=["POST"])
def end_session(session_id: str):
    """End a tutoring session."""
    result = tutor_engine.end_session(session_id)
    if not result:
        raise NotFoundError("Session not found")
    return jsonify(result)
