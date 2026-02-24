"""AI tutor session routes with SSE streaming."""

import json
import os
import re
import time

from flask import Blueprint, request, jsonify, Response

from api.errors import ValidationError, NotFoundError
from api.middleware.auth import get_current_user, get_current_user_id, login_required
from api.services import tutor_engine
from api.services.database import get_db
from api.services.prompt_library import MODES
from api.services.tier_limits import check_tier_limit

_PERF_TAG_RE = re.compile(r"<performance>[\s\S]*?</performance>")
_DEBUG_LOG_PATH = r"c:\Dev\LawFlow\.claude\worktrees\charming-dewdney\.cursor\debug.log"


def _debug_log(hypothesis_id: str, message: str, data: dict):
    # #region agent log
    try:
        os.makedirs(os.path.dirname(_DEBUG_LOG_PATH), exist_ok=True)
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "id": f"log_{int(time.time() * 1000)}_tutor_route",
                        "timestamp": int(time.time() * 1000),
                        "runId": "pre-fix",
                        "hypothesisId": hypothesis_id,
                        "location": "api/routes/tutor.py:get_session",
                        "message": message,
                        "data": data,
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion

bp = Blueprint("tutor", __name__, url_prefix="/api/tutor")


@bp.before_request
@login_required
def require_auth():
    return None


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
    user_id = get_current_user_id()
    data = request.get_json()
    if not data:
        raise ValidationError("JSON body required")

    mode = data.get("mode", "explain")
    if mode not in MODES:
        raise ValidationError(f"Invalid mode. Available: {', '.join(MODES.keys())}")

    with get_db() as db:
        check_tier_limit(db, get_current_user(), "tutor_sessions_daily")

    session = tutor_engine.create_session(
        mode=mode,
        subject=data.get("subject"),
        topics=data.get("topics"),
        user_id=user_id,
    )
    return jsonify(session), 201


@bp.route("/session/<session_id>", methods=["GET"])
def get_session(session_id: str):
    """Get session details with message history."""
    user_id = get_current_user_id()
    # #region agent log
    _debug_log(
        "H10",
        "Tutor session fetch requested",
        {
            "session_id_len": len(session_id),
            "session_id_prefix": session_id[:8],
        },
    )
    # #endregion
    session = tutor_engine.get_session(session_id, user_id=user_id)
    if not session:
        # #region agent log
        _debug_log(
            "H10",
            "Tutor session not found",
            {
                "session_id_len": len(session_id),
                "session_id_prefix": session_id[:8],
            },
        )
        # #endregion
        raise NotFoundError("Session not found")
    # #region agent log
    _debug_log(
        "H10",
        "Tutor session found",
        {
            "session_id_prefix": session_id[:8],
            "messages_count": len(session.get("messages", [])),
        },
    )
    # #endregion
    return jsonify(session)


@bp.route("/message", methods=["POST"])
def send_message():
    """Send a message and stream Claude's response via SSE."""
    user_id = get_current_user_id()
    data = request.get_json()
    if not data:
        raise ValidationError("JSON body required")

    session_id = data.get("session_id")
    content = data.get("content")

    if not session_id or not content:
        raise ValidationError("session_id and content are required")
    header_key = request.headers.get("X-Anthropic-Api-Key", "")

    def generate():
        perf_buf = ""
        try:
            for chunk in tutor_engine.send_message(
                session_id,
                content,
                api_key_override=header_key,
                user_id=user_id,
            ):
                text = perf_buf + chunk
                perf_buf = ""

                perf_start = text.find("<performance")
                if perf_start != -1:
                    perf_end = text.find("</performance>")
                    if perf_end != -1:
                        text = text[:perf_start] + text[perf_end + len("</performance>"):]
                    else:
                        perf_buf = text[perf_start:]
                        text = text[:perf_start]

                text = _PERF_TAG_RE.sub("", text)
                if text:
                    yield f"data: {json.dumps(text)}\n\n"
            yield "data: [DONE]\n\n"
        except ValueError as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@bp.route("/recent", methods=["GET"])
def recent_sessions():
    """Get the most recent study sessions."""
    user_id = get_current_user_id()
    limit = request.args.get("limit", 5, type=int)
    from api.services.database import get_db
    from api.models.session import StudySession
    with get_db() as db:
        sessions = (
            db.query(StudySession)
            .filter(StudySession.user_id == user_id)
            .order_by(StudySession.started_at.desc())
            .limit(limit)
            .all()
        )
        return jsonify([s.to_dict() for s in sessions])


@bp.route("/session/<session_id>/end", methods=["POST"])
def end_session(session_id: str):
    """End a tutoring session."""
    user_id = get_current_user_id()
    result = tutor_engine.end_session(session_id, user_id=user_id)
    if not result:
        raise NotFoundError("Session not found")

    # Award points if student actually engaged (5+ messages)
    try:
        msg_count = result.get("messages_count") or 0
        if msg_count >= 5:
            from api.services.rewards_engine import award_points
            perf = result.get("performance_score") or 0
            base = 30 + (10 if perf > 70 else 0)
            reward = award_points(
                "tutor_session", session_id,
                f"Completed tutor session ({result.get('tutor_mode', 'study')})",
                base_amount=base,
                metadata={"subject": result.get("subject"), "mode": result.get("tutor_mode")},
                user_id=user_id,
            )
            result["points_awarded"] = reward
    except Exception:
        pass  # Don't break tutor flow if rewards fail

    return jsonify(result)
