"""Exam simulator routes — generate, grade, and review practice exams."""

from flask import Blueprint, jsonify, request

from api.errors import ValidationError, NotFoundError
from api.middleware.auth import get_current_user, get_current_user_id, login_required
from api.services.database import get_db
from api.services.exam_simulator import (
    generate_exam,
    grade_answer,
    complete_exam,
    get_exam_results,
    get_exam_history,
)
from api.services.tier_limits import check_tier_limit

bp = Blueprint("exam", __name__, url_prefix="/api/exam")


@bp.before_request
@login_required
def require_auth():
    return None


@bp.route("/generate", methods=["POST"])
def create_exam():
    """Generate a practice exam.

    Body: {
        subject: string,
        format: "essay" | "mc" | "mixed" | "issue_spot",
        num_questions: int (default 5),
        time_minutes: int (default 60)
    }
    """
    user_id = get_current_user_id()
    data = request.get_json(force=True)
    subject = data.get("subject")
    if not subject:
        raise ValidationError("subject is required")

    exam_format = data.get("format", "mixed")
    num_questions = data.get("num_questions", 5)
    time_minutes = data.get("time_minutes", 60)

    if num_questions < 1 or num_questions > 20:
        raise ValidationError("num_questions must be 1-20")

    try:
        with get_db() as db:
            check_tier_limit(db, get_current_user(), "exam_generations_daily")
        exam = generate_exam(
            subject=subject,
            exam_format=exam_format,
            num_questions=num_questions,
            time_minutes=time_minutes,
            user_id=user_id,
        )
    except (ValueError, RuntimeError) as e:
        raise ValidationError(str(e))

    return jsonify(exam)


@bp.route("/answer", methods=["POST"])
def submit_answer():
    """Submit and grade a single answer.

    Body: { question_id: string, answer: string }
    """
    user_id = get_current_user_id()
    data = request.get_json(force=True)
    question_id = data.get("question_id")
    answer = data.get("answer", "")

    if not question_id:
        raise ValidationError("question_id is required")

    try:
        result = grade_answer(question_id, answer, user_id=user_id)
    except ValueError as e:
        raise NotFoundError(str(e))
    except RuntimeError as e:
        raise ValidationError(str(e))

    return jsonify(result)


@bp.route("/complete/<assessment_id>", methods=["POST"])
def finish_exam(assessment_id: str):
    """Finalize an exam — compute scores, update mastery, get summary."""
    user_id = get_current_user_id()
    try:
        results = complete_exam(assessment_id, user_id=user_id)
    except ValueError as e:
        raise NotFoundError(str(e))

    return jsonify(results)


@bp.route("/results/<assessment_id>", methods=["GET"])
def exam_results(assessment_id: str):
    """Get full results for a completed exam."""
    results = get_exam_results(assessment_id, user_id=get_current_user_id())
    if not results:
        raise NotFoundError(f"Assessment {assessment_id} not found")
    return jsonify(results)


@bp.route("/history", methods=["GET"])
def exam_history():
    """Get past exam attempts."""
    user_id = get_current_user_id()
    subject = request.args.get("subject")
    limit = request.args.get("limit", 10, type=int)
    history = get_exam_history(subject=subject, limit=limit, user_id=user_id)
    return jsonify(history)
