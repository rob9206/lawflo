"""AutoTeach routes — intelligent study orchestration."""

import json
import os
import re
import time

from flask import Blueprint, request, jsonify, Response

from api.errors import ValidationError, NotFoundError
from api.middleware.auth import get_current_user, get_current_user_id, login_required
from api.services.auto_teach import generate_teaching_plan, get_next_topic
from api.services.exam_analyzer import analyze_exam, get_exam_blueprints
from api.services import tutor_engine
from api.services.database import get_db
from api.services.tier_limits import check_tier_limit

_PERF_TAG_RE = re.compile(r"<performance>[\s\S]*?</performance>")
_PRACTICE_TAG_RE = re.compile(r"<practice_questions>[\s\S]*?</practice_questions>")
_DEBUG_LOG_PATH = r"c:\Dev\LawFlow\.claude\worktrees\charming-dewdney\.cursor\debug.log"


def _debug_log(hypothesis_id: str, message: str, data: dict):
    # #region agent log
    try:
        os.makedirs(os.path.dirname(_DEBUG_LOG_PATH), exist_ok=True)
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "id": f"log_{int(time.time() * 1000)}_auto_teach_route",
                        "timestamp": int(time.time() * 1000),
                        "runId": "pre-fix",
                        "hypothesisId": hypothesis_id,
                        "location": "api/routes/auto_teach.py:start_auto_session",
                        "message": message,
                        "data": data,
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion

bp = Blueprint("auto_teach", __name__, url_prefix="/api/auto-teach")


@bp.before_request
@login_required
def require_auth():
    return None


@bp.route("/plan/<subject>", methods=["GET"])
def get_teaching_plan(subject: str):
    """Generate a prioritized teaching plan for a subject.

    Query params:
        max_topics: int (default 10)
        available_minutes: int (optional - constrain plan to time budget)
    """
    user_id = get_current_user_id()
    max_topics = request.args.get("max_topics", 10, type=int)
    available_minutes = request.args.get("available_minutes", type=int)

    plan = generate_teaching_plan(
        subject=subject,
        max_topics=max_topics,
        available_minutes=available_minutes,
        user_id=user_id,
    )
    return jsonify(plan)


@bp.route("/next/<subject>", methods=["GET"])
def next_topic(subject: str):
    """Get the single highest-priority topic to study right now."""
    result = get_next_topic(subject, user_id=get_current_user_id())
    if not result:
        return jsonify({"message": f"No topics found for {subject}"}), 404
    return jsonify(result)


@bp.route("/start", methods=["POST"])
def start_auto_session():
    """Start an auto-teach session: creates a tutor session AND sends the
    first message automatically, so the tutor immediately starts teaching
    the right topic in the right mode.

    Body: {
        "subject": "contracts",
        "topic": "consideration"  (optional — auto-picks highest priority if omitted)
    }
    """
    user_id = get_current_user_id()
    data = request.get_json()
    if not data or "subject" not in data:
        raise ValidationError("subject is required")

    subject = data["subject"]
    topic = data.get("topic")
    available_minutes = data.get("available_minutes")
    header_key = request.headers.get("X-Anthropic-Api-Key", "")
    # #region agent log
    _debug_log(
        "H2",
        "Received auto-teach start request headers",
        {
            "subject": subject,
            "has_topic": bool(topic),
            "available_minutes": available_minutes,
            "header_present": bool(header_key),
            "header_len": len(header_key.strip()),
            "header_looks_anthropic": header_key.strip().startswith("sk-ant-"),
        },
    )
    # #endregion

    # If no topic specified, auto-pick the highest priority one
    if not topic:
        next_t = get_next_topic(subject, available_minutes=available_minutes, user_id=user_id)
        if not next_t:
            return jsonify({"error": f"No topics found for {subject}"}), 404
        auto_session = next_t.get("auto_session")
        if not auto_session:
            return jsonify({
                "error": (
                    f"No study session could be generated for {subject}. "
                    "Try a longer time budget."
                )
            }), 422
        topic = next_t["topic"]
        mode = next_t["recommended_mode"]
        opening = auto_session["opening_message"]
    else:
        from api.services.auto_teach import select_teaching_mode, _build_opening_message
        from api.services.database import get_db
        from api.models.student import TopicMastery
        from api.services.exam_analyzer import get_aggregated_topic_weights

        with get_db() as db:
            t = db.query(TopicMastery).filter_by(
                user_id=user_id,
                subject=subject,
                topic=topic,
            ).first()
            mastery = t.mastery_score if t else 0.0
            display = t.display_name if t else topic

        exam_weights = get_aggregated_topic_weights(subject, user_id=user_id)
        has_exam_data = bool(exam_weights)
        mode, mode_reason = select_teaching_mode(mastery, has_exam_data)

        from api.services.auto_teach import TeachingTarget
        target = TeachingTarget(
            subject=subject,
            topic=topic,
            display_name=display,
            priority_score=0,
            mastery=mastery,
            exam_weight=exam_weights.get(topic, 0),
            recommended_mode=mode,
            mode_reason=mode_reason,
            knowledge_chunks_available=0,
            time_estimate_minutes=max(5, int((100 - mastery) * 0.5)),
        )
        opening = _build_opening_message(target, has_exam_data, available_minutes)

    with get_db() as db:
        check_tier_limit(db, get_current_user(), "auto_teach_sessions_daily")

    # Create the session
    session = tutor_engine.create_session(
        mode=mode,
        subject=subject,
        topics=[topic],
        available_minutes=available_minutes,
        session_type="auto_teach",
        user_id=user_id,
    )

    # Stream the opening response, filtering <performance> metadata
    def generate():
        perf_buf = ""
        try:
            for chunk in tutor_engine.send_message(
                session["id"],
                opening,
                api_key_override=header_key,
                user_id=user_id,
            ):
                text = perf_buf + chunk
                perf_buf = ""

                # Buffer incomplete metadata tags until they close
                for tag_name in ("performance", "practice_questions"):
                    tag_start = text.find(f"<{tag_name}")
                    if tag_start != -1:
                        tag_end = text.find(f"</{tag_name}>")
                        if tag_end != -1:
                            text = text[:tag_start] + text[tag_end + len(f"</{tag_name}>"):]
                        else:
                            perf_buf = text[tag_start:]
                            text = text[:tag_start]

                # Strip any fully-formed tags that span multiple chunks
                text = _PERF_TAG_RE.sub("", text)
                text = _PRACTICE_TAG_RE.sub("", text)
                if text:
                    yield f"data: {json.dumps(text)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            # #region agent log
            _debug_log(
                "H5",
                "AutoTeach stream failed",
                {
                    "exception_type": type(e).__name__,
                    "error_excerpt": str(e)[:220],
                },
            )
            # #endregion
            yield f"data: [ERROR][DBGv2] {str(e)}\n\n"

    # Return session info + streaming response
    # We use a special header so the frontend knows the session ID
    response = Response(generate(), mimetype="text/event-stream")
    response.headers["X-Session-Id"] = session["id"]
    response.headers["X-Tutor-Mode"] = mode
    response.headers["X-Topic"] = topic
    response.headers["X-Debug-AutoTeach-Version"] = "DBGv2"
    return response


@bp.route("/exam/analyze/<document_id>", methods=["POST"])
def analyze_exam_document(document_id: str):
    """Trigger exam analysis on an uploaded exam document.

    This sends the exam text to Claude to extract:
    - Topics tested and their weights
    - Question formats
    - Professor patterns
    - High-yield summary
    """
    try:
        blueprint = analyze_exam(document_id, user_id=get_current_user_id())
        return jsonify(blueprint), 201
    except ValueError as e:
        raise ValidationError(str(e))


@bp.route("/exam/blueprints", methods=["GET"])
def list_exam_blueprints():
    """List all exam blueprints, optionally filtered by subject."""
    subject = request.args.get("subject")
    blueprints = get_exam_blueprints(subject, user_id=get_current_user_id())
    return jsonify(blueprints)
