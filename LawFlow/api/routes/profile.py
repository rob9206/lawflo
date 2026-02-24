"""Profile and settings routes."""

import os
import re
from pathlib import Path

from flask import Blueprint, jsonify, request

from api.config import config
from api.middleware.auth import get_current_user, get_current_user_id, login_required
from api.services.database import get_db
from api.models.student import SubjectMastery, TopicMastery
from api.models.session import StudySession, SessionMessage
from api.models.document import Document
from api.models.assessment import Assessment, AssessmentQuestion
from api.models.study_plan import StudyPlan, PlanTask
from api.models.review import SpacedRepetitionCard
from api.models.exam_blueprint import ExamBlueprint, ExamTopicWeight
from api.models.rewards import PointLedger, Achievement, RewardsProfile
from api.models.user import User
from api.services.subject_taxonomy import seed_subject_taxonomy
from api.services.achievement_definitions import seed_achievements

bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@bp.before_request
@login_required
def require_auth():
    return None


@bp.route("/stats", methods=["GET"])
def profile_stats():
    """Aggregate stats for the profile page."""
    user_id = get_current_user_id()
    with get_db() as db:
        # Count records across all tables
        total_subjects = db.query(SubjectMastery).filter_by(user_id=user_id).count()
        total_topics = db.query(TopicMastery).filter_by(user_id=user_id).count()
        total_sessions = db.query(StudySession).filter_by(user_id=user_id).count()
        total_assessments = db.query(Assessment).filter_by(user_id=user_id).count()
        total_documents = db.query(Document).filter_by(user_id=user_id).count()
        total_flashcards = db.query(SpacedRepetitionCard).filter_by(user_id=user_id).count()
        user = db.query(User).filter_by(id=user_id).first()
        
        # Calculate overall mastery and study hours
        subjects = db.query(SubjectMastery).filter_by(user_id=user_id).all()
        overall_mastery = (
            sum(s.mastery_score for s in subjects) / len(subjects)
            if subjects else 0
        )
        total_study_hours = sum(s.total_study_time_minutes or 0 for s in subjects) / 60.0
        
        return jsonify({
            "total_subjects": total_subjects,
            "total_topics": total_topics,
            "overall_mastery": round(overall_mastery, 1),
            "total_study_hours": round(total_study_hours, 1),
            "total_sessions": total_sessions,
            "total_assessments": total_assessments,
            "total_documents": total_documents,
            "total_flashcards": total_flashcards,
            "tier": (user.tier if user else "free"),
        })


@bp.route("/reset-progress", methods=["POST"])
def reset_progress():
    """Reset mastery and study data only (keeps uploaded documents and knowledge chunks)."""
    user_id = get_current_user_id()
    with get_db() as db:
        # Delete study-related data but keep documents and knowledge
        db.query(ExamTopicWeight).filter_by(user_id=user_id).delete()
        db.query(ExamBlueprint).filter_by(user_id=user_id).delete()
        db.query(PlanTask).filter_by(user_id=user_id).delete()
        db.query(StudyPlan).filter_by(user_id=user_id).delete()
        db.query(SpacedRepetitionCard).filter_by(user_id=user_id).delete()
        db.query(AssessmentQuestion).filter_by(user_id=user_id).delete()
        db.query(Assessment).filter_by(user_id=user_id).delete()
        db.query(SessionMessage).filter_by(user_id=user_id).delete()
        db.query(StudySession).filter_by(user_id=user_id).delete()
        db.query(TopicMastery).filter_by(user_id=user_id).delete()
        db.query(SubjectMastery).filter_by(user_id=user_id).delete()
        db.query(PointLedger).filter_by(user_id=user_id).delete()
        db.query(Achievement).filter_by(user_id=user_id).delete()
        db.query(RewardsProfile).filter_by(user_id=user_id).delete()
    seed_subject_taxonomy(user_id=user_id)
    seed_achievements(user_id=user_id)
    return jsonify({"status": "ok"})


@bp.route("/reset-all", methods=["POST"])
def reset_all():
    """Delete all data owned by the current user."""
    user_id = get_current_user_id()
    with get_db() as db:
        db.query(ExamTopicWeight).filter_by(user_id=user_id).delete()
        db.query(ExamBlueprint).filter_by(user_id=user_id).delete()
        db.query(PlanTask).filter_by(user_id=user_id).delete()
        db.query(StudyPlan).filter_by(user_id=user_id).delete()
        db.query(SpacedRepetitionCard).filter_by(user_id=user_id).delete()
        db.query(AssessmentQuestion).filter_by(user_id=user_id).delete()
        db.query(Assessment).filter_by(user_id=user_id).delete()
        db.query(SessionMessage).filter_by(user_id=user_id).delete()
        db.query(StudySession).filter_by(user_id=user_id).delete()
        db.query(TopicMastery).filter_by(user_id=user_id).delete()
        db.query(SubjectMastery).filter_by(user_id=user_id).delete()
        db.query(Document).filter_by(user_id=user_id).delete()
        db.query(PointLedger).filter_by(user_id=user_id).delete()
        db.query(Achievement).filter_by(user_id=user_id).delete()
        db.query(RewardsProfile).filter_by(user_id=user_id).delete()
    seed_subject_taxonomy(user_id=user_id)
    seed_achievements(user_id=user_id)
    return jsonify({"status": "ok"})


# ── API Key Management ─────────────────────────────────────────────────────

def _mask_key(key: str) -> str:
    """Return masked version showing only last 4 chars."""
    if not key or len(key) < 8:
        return ""
    return "•" * 12 + key[-4:]


def _env_path() -> Path:
    override = os.getenv("LAWFLOW_ENV_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parent.parent.parent / ".env"


def _update_env_key(key_name: str, key_value: str) -> None:
    """Update or insert a key=value pair in the .env file."""
    env_file = _env_path()
    if not env_file.exists():
        env_file.write_text(f"{key_name}={key_value}\n")
        return

    content = env_file.read_text()
    pattern = re.compile(rf"^{re.escape(key_name)}=.*$", re.MULTILINE)
    if pattern.search(content):
        content = pattern.sub(f"{key_name}={key_value}", content)
    else:
        content = content.rstrip() + f"\n{key_name}={key_value}\n"
    env_file.write_text(content)


@bp.route("/api-keys", methods=["GET"])
def get_api_keys():
    """Return masked status of configured API keys."""
    return jsonify({
        "anthropic": {
            "configured": bool(config.ANTHROPIC_API_KEY and
                               config.ANTHROPIC_API_KEY != "sk-ant-your-key-here"),
            "masked": _mask_key(config.ANTHROPIC_API_KEY)
                      if config.ANTHROPIC_API_KEY != "sk-ant-your-key-here" else "",
            "model": config.CLAUDE_MODEL,
        },
    })


@bp.route("/api-keys", methods=["POST"])
def save_api_keys():
    """Save API key to .env and reload in-memory config."""
    body = request.get_json(force=True)
    updated = []

    anthropic_key = body.get("anthropic_key", "").strip()
    if anthropic_key:
        _update_env_key("ANTHROPIC_API_KEY", anthropic_key)
        config.ANTHROPIC_API_KEY = anthropic_key
        updated.append("anthropic")

    model = body.get("model", "").strip()
    if model:
        _update_env_key("CLAUDE_MODEL", model)
        config.CLAUDE_MODEL = model
        updated.append("model")

    if not updated:
        return jsonify({"error": "No keys provided"}), 400

    return jsonify({"status": "ok", "updated": updated})