"""AutoTeach routes — intelligent study orchestration."""

import json
import re

from flask import Blueprint, request, jsonify, Response

from api.errors import ValidationError, NotFoundError
from api.services.auto_teach import generate_teaching_plan, get_next_topic
from api.services.exam_analyzer import analyze_exam, get_exam_blueprints
from api.services import tutor_engine

_PERF_TAG_RE = re.compile(r"<performance>[\s\S]*?</performance>")

bp = Blueprint("auto_teach", __name__, url_prefix="/api/auto-teach")


@bp.route("/plan/<subject>", methods=["GET"])
def get_teaching_plan(subject: str):
    """Generate a prioritized teaching plan for a subject.

    Query params:
        max_topics: int (default 10)
        available_minutes: int (optional - constrain plan to time budget)
    """
    max_topics = request.args.get("max_topics", 10, type=int)
    available_minutes = request.args.get("available_minutes", type=int)

    plan = generate_teaching_plan(
        subject=subject,
        max_topics=max_topics,
        available_minutes=available_minutes,
    )
    return jsonify(plan)


@bp.route("/next/<subject>", methods=["GET"])
def next_topic(subject: str):
    """Get the single highest-priority topic to study right now."""
    result = get_next_topic(subject)
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
    data = request.get_json()
    if not data or "subject" not in data:
        raise ValidationError("subject is required")

    subject = data["subject"]
    topic = data.get("topic")

    # If no topic specified, auto-pick the highest priority one
    if not topic:
        next_t = get_next_topic(subject)
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
        # Compute mode for the specified topic
        from api.services.auto_teach import select_teaching_mode, compute_priority
        from api.services.database import get_db
        from api.models.student import TopicMastery

        with get_db() as db:
            t = db.query(TopicMastery).filter_by(subject=subject, topic=topic).first()
            mastery = t.mastery_score if t else 0.0
            display = t.display_name if t else topic

        mode, _ = select_teaching_mode(mastery, False)
        opening = f"Teach me about {display}. My current mastery is {mastery:.0f}%. Focus on what I need to know for the exam."

    # Create the session
    session = tutor_engine.create_session(
        mode=mode,
        subject=subject,
        topics=[topic],
    )

    # Stream the opening response, filtering <performance> metadata
    def generate():
        perf_buf = ""
        try:
            for chunk in tutor_engine.send_message(session["id"], opening):
                text = perf_buf + chunk
                perf_buf = ""

                # Buffer incomplete <performance> tags until they close
                perf_start = text.find("<performance")
                if perf_start != -1:
                    perf_end = text.find("</performance>")
                    if perf_end != -1:
                        text = text[:perf_start] + text[perf_end + len("</performance>"):]
                    else:
                        perf_buf = text[perf_start:]
                        text = text[:perf_start]

                # Strip any fully-formed tags that span multiple chunks
                text = _PERF_TAG_RE.sub("", text)
                if text:
                    yield f"data: {json.dumps(text)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    # Return session info + streaming response
    # We use a special header so the frontend knows the session ID
    response = Response(generate(), mimetype="text/event-stream")
    response.headers["X-Session-Id"] = session["id"]
    response.headers["X-Tutor-Mode"] = mode
    response.headers["X-Topic"] = topic
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
        blueprint = analyze_exam(document_id)
        return jsonify(blueprint), 201
    except ValueError as e:
        raise ValidationError(str(e))


@bp.route("/exam/blueprints", methods=["GET"])
def list_exam_blueprints():
    """List all exam blueprints, optionally filtered by subject."""
    subject = request.args.get("subject")
    blueprints = get_exam_blueprints(subject)
    return jsonify(blueprints)
