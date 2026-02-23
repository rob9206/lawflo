"""Profile and settings routes."""

import io
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from api.config import config
from api.errors import ValidationError
from api.services.database import get_db, reset_database
from api.models.student import SubjectMastery, TopicMastery
from api.models.session import StudySession, SessionMessage
from api.models.document import Document
from api.models.assessment import Assessment, AssessmentQuestion
from api.models.study_plan import StudyPlan, PlanTask
from api.models.review import SpacedRepetitionCard
from api.models.exam_blueprint import ExamBlueprint, ExamTopicWeight
from api.models.rewards import Achievement, RewardsProfile, PointLedger

bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@bp.route("/stats", methods=["GET"])
def profile_stats():
    """Aggregate stats for the profile page."""
    with get_db() as db:
        # Count records across all tables
        total_subjects = db.query(SubjectMastery).count()
        total_topics = db.query(TopicMastery).count()
        total_sessions = db.query(StudySession).count()
        total_assessments = db.query(Assessment).count()
        total_documents = db.query(Document).count()
        total_flashcards = db.query(SpacedRepetitionCard).count()
        
        # Calculate overall mastery and study hours
        subjects = db.query(SubjectMastery).all()
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
        })


@bp.route("/reset-progress", methods=["POST"])
def reset_progress():
    """Reset mastery and study data only (keeps uploaded documents and knowledge chunks)."""
    with get_db() as db:
        # Delete study-related data but keep documents and knowledge
        db.query(ExamTopicWeight).delete()
        db.query(ExamBlueprint).delete()
        db.query(PlanTask).delete()
        db.query(StudyPlan).delete()
        db.query(SpacedRepetitionCard).delete()
        db.query(AssessmentQuestion).delete()
        db.query(Assessment).delete()
        db.query(SessionMessage).delete()
        db.query(StudySession).delete()
        db.query(TopicMastery).delete()
        db.query(SubjectMastery).delete()
        
        return jsonify({"status": "ok"})


@bp.route("/reset-all", methods=["POST"])
def reset_all():
    """Full nuclear reset - drops and recreates all tables."""
    reset_database()
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


# ── Data Export / Import ───────────────────────────────────────────────────

_EXPORT_VERSION = "1"


@bp.route("/export", methods=["GET"])
def export_data():
    """Export all study data as a JSON backup file."""
    with get_db() as db:
        subjects = [s.to_dict() for s in db.query(SubjectMastery).all()]
        topics = [t.to_dict() for t in db.query(TopicMastery).all()]

        sessions = []
        for s in db.query(StudySession).all():
            sd = s.to_dict()
            sd["messages"] = [m.to_dict() for m in s.messages]
            sessions.append(sd)

        assessments = []
        for a in db.query(Assessment).all():
            ad = a.to_dict()
            ad["questions"] = [q.to_dict() for q in a.questions]
            assessments.append(ad)

        plans = []
        for p in db.query(StudyPlan).all():
            pd = p.to_dict()
            pd["tasks"] = [t.to_dict() for t in p.tasks]
            plans.append(pd)

        flashcards = [c.to_dict() for c in db.query(SpacedRepetitionCard).all()]
        achievements = [a.to_dict() for a in db.query(Achievement).all()]
        rewards_profiles = [r.to_dict() for r in db.query(RewardsProfile).all()]

    payload = {
        "version": _EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "subject_mastery": subjects,
        "topic_mastery": topics,
        "study_sessions": sessions,
        "assessments": assessments,
        "study_plans": plans,
        "flashcards": flashcards,
        "achievements": achievements,
        "rewards_profiles": rewards_profiles,
    }

    buf = io.BytesIO(json.dumps(payload, indent=2).encode("utf-8"))
    buf.seek(0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return send_file(
        buf,
        mimetype="application/json",
        as_attachment=True,
        download_name=f"lawflow_backup_{timestamp}.json",
    )


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


@bp.route("/import", methods=["POST"])
def import_data():
    """Import a JSON backup produced by /export.

    Existing rows with the same primary key are skipped (INSERT OR IGNORE
    semantics) so importing is safe to run multiple times.
    """
    if "file" not in request.files:
        raise ValidationError("No file provided")

    uploaded = request.files["file"]
    try:
        payload = json.loads(uploaded.read())
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValidationError("Invalid JSON file")

    if not isinstance(payload, dict):
        raise ValidationError("Invalid backup format")

    counts: dict[str, int] = {}

    with get_db() as db:
        # ── Subject mastery ──
        n = 0
        for row in payload.get("subject_mastery", []):
            if not db.query(SubjectMastery).filter_by(id=row["id"]).first():
                db.add(SubjectMastery(
                    id=row["id"],
                    subject=row["subject"],
                    display_name=row["display_name"],
                    mastery_score=row.get("mastery_score", 0.0),
                    total_study_time_minutes=row.get("total_study_time_minutes", 0),
                    sessions_count=row.get("sessions_count", 0),
                    assessments_count=row.get("assessments_count", 0),
                    last_studied_at=_parse_dt(row.get("last_studied_at")),
                ))
                n += 1
        counts["subject_mastery"] = n

        # ── Topic mastery ──
        n = 0
        for row in payload.get("topic_mastery", []):
            if not db.query(TopicMastery).filter_by(id=row["id"]).first():
                db.add(TopicMastery(
                    id=row["id"],
                    subject=row["subject"],
                    topic=row["topic"],
                    display_name=row["display_name"],
                    mastery_score=row.get("mastery_score", 0.0),
                    confidence=row.get("confidence", 0.0),
                    exposure_count=row.get("exposure_count", 0),
                    correct_count=row.get("correct_count", 0),
                    incorrect_count=row.get("incorrect_count", 0),
                    last_tested_at=_parse_dt(row.get("last_tested_at")),
                    last_studied_at=_parse_dt(row.get("last_studied_at")),
                ))
                n += 1
        counts["topic_mastery"] = n

        # ── Study sessions + messages ──
        n_sessions = 0
        n_messages = 0
        for row in payload.get("study_sessions", []):
            if not db.query(StudySession).filter_by(id=row["id"]).first():
                db.add(StudySession(
                    id=row["id"],
                    session_type=row["session_type"],
                    tutor_mode=row.get("tutor_mode"),
                    subject=row.get("subject"),
                    topics=json.dumps(row.get("topics", [])),
                    started_at=_parse_dt(row.get("started_at")) or datetime.now(timezone.utc),
                    ended_at=_parse_dt(row.get("ended_at")),
                    duration_minutes=row.get("duration_minutes"),
                    messages_count=row.get("messages_count", 0),
                    performance_score=row.get("performance_score"),
                    notes=row.get("notes"),
                ))
                n_sessions += 1
                for msg in row.get("messages", []):
                    if not db.query(SessionMessage).filter_by(id=msg["id"]).first():
                        db.add(SessionMessage(
                            id=msg["id"],
                            session_id=row["id"],
                            role=msg["role"],
                            content=msg["content"],
                            message_index=msg["message_index"],
                            metadata_json=json.dumps(msg.get("metadata")) if msg.get("metadata") else None,
                            created_at=_parse_dt(msg.get("created_at")),
                        ))
                        n_messages += 1
        counts["study_sessions"] = n_sessions
        counts["session_messages"] = n_messages

        # ── Assessments + questions ──
        n_assessments = 0
        n_questions = 0
        for row in payload.get("assessments", []):
            if not db.query(Assessment).filter_by(id=row["id"]).first():
                db.add(Assessment(
                    id=row["id"],
                    session_id=row.get("session_id"),
                    assessment_type=row["assessment_type"],
                    subject=row["subject"],
                    topics=json.dumps(row.get("topics", [])),
                    total_questions=row["total_questions"],
                    score=row.get("score"),
                    time_limit_minutes=row.get("time_limit_minutes"),
                    time_taken_minutes=row.get("time_taken_minutes"),
                    is_timed=int(bool(row.get("is_timed", False))),
                    feedback_summary=row.get("feedback_summary"),
                    created_at=_parse_dt(row.get("created_at")),
                    completed_at=_parse_dt(row.get("completed_at")),
                ))
                n_assessments += 1
                for q in row.get("questions", []):
                    if not db.query(AssessmentQuestion).filter_by(id=q["id"]).first():
                        db.add(AssessmentQuestion(
                            id=q["id"],
                            assessment_id=row["id"],
                            question_index=q["question_index"],
                            question_type=q["question_type"],
                            question_text=q["question_text"],
                            options=json.dumps(q["options"]) if q.get("options") else None,
                            correct_answer=q.get("correct_answer"),
                            student_answer=q.get("student_answer"),
                            is_correct=int(bool(q["is_correct"])) if q.get("is_correct") is not None else None,
                            score=q.get("score"),
                            feedback=q.get("feedback"),
                            subject=q.get("subject"),
                            topic=q.get("topic"),
                            difficulty=q.get("difficulty", 50),
                        ))
                        n_questions += 1
        counts["assessments"] = n_assessments
        counts["assessment_questions"] = n_questions

        # ── Study plans + tasks ──
        n_plans = 0
        n_tasks = 0
        for row in payload.get("study_plans", []):
            if not db.query(StudyPlan).filter_by(id=row["id"]).first():
                db.add(StudyPlan(
                    id=row["id"],
                    name=row["name"],
                    exam_date=_parse_dt(row.get("exam_date")),
                    subjects=json.dumps(row.get("subjects", [])),
                    weekly_hours=row.get("weekly_hours", 20.0),
                    strategy_notes=row.get("strategy_notes"),
                    is_active=int(bool(row.get("is_active", True))),
                    created_at=_parse_dt(row.get("created_at")),
                ))
                n_plans += 1
                for t in row.get("tasks", []):
                    if not db.query(PlanTask).filter_by(id=t["id"]).first():
                        scheduled = _parse_dt(t.get("scheduled_date"))
                        db.add(PlanTask(
                            id=t["id"],
                            plan_id=row["id"],
                            subject=t["subject"],
                            topic=t.get("topic"),
                            task_type=t["task_type"],
                            description=t["description"],
                            scheduled_date=scheduled.date() if scheduled else None,
                            estimated_minutes=t.get("estimated_minutes", 30),
                            priority=t.get("priority", 50),
                            is_completed=int(bool(t.get("is_completed", False))),
                            completed_at=_parse_dt(t.get("completed_at")),
                        ))
                        n_tasks += 1
        counts["study_plans"] = n_plans
        counts["plan_tasks"] = n_tasks

        # ── Flashcards ──
        n = 0
        for row in payload.get("flashcards", []):
            if not db.query(SpacedRepetitionCard).filter_by(id=row["id"]).first():
                db.add(SpacedRepetitionCard(
                    id=row["id"],
                    chunk_id=row.get("chunk_id"),
                    subject=row["subject"],
                    topic=row.get("topic"),
                    front=row["front"],
                    back=row["back"],
                    card_type=row.get("card_type", "concept"),
                    ease_factor=row.get("ease_factor", 2.5),
                    interval_days=row.get("interval_days", 1),
                    repetitions=row.get("repetitions", 0),
                    next_review=_parse_dt(row.get("next_review")),
                    last_reviewed=_parse_dt(row.get("last_reviewed")),
                ))
                n += 1
        counts["flashcards"] = n

        # ── Achievements ──
        n = 0
        for row in payload.get("achievements", []):
            existing = db.query(Achievement).filter_by(achievement_key=row["achievement_key"]).first()
            if existing:
                # Merge progress values (keep the higher ones)
                if row.get("current_value", 0) > existing.current_value:
                    existing.current_value = row["current_value"]
                if row.get("unlocked_at") and not existing.unlocked_at:
                    existing.unlocked_at = _parse_dt(row["unlocked_at"])
            else:
                db.add(Achievement(
                    id=row["id"],
                    achievement_key=row["achievement_key"],
                    title=row["title"],
                    description=row["description"],
                    icon=row.get("icon", "trophy"),
                    rarity=row.get("rarity", "common"),
                    points_awarded=row.get("points_awarded", 0),
                    unlocked_at=_parse_dt(row.get("unlocked_at")),
                    target_value=row.get("target_value", 1),
                    current_value=row.get("current_value", 0),
                ))
                n += 1
        counts["achievements"] = n

        # ── Rewards profiles ──
        n = 0
        for row in payload.get("rewards_profiles", []):
            if not db.query(RewardsProfile).filter_by(id=row["id"]).first():
                db.add(RewardsProfile(
                    id=row["id"],
                    active_title=row.get("active_title", "Law Student"),
                    current_streak=row.get("current_streak", 0),
                    longest_streak=row.get("longest_streak", 0),
                    last_active_date=row.get("last_active_date"),  # stored as "YYYY-MM-DD" string
                    total_earned=row.get("total_earned", 0),
                    level=row.get("level", 1),
                ))
                n += 1
        counts["rewards_profiles"] = n

    return jsonify({"status": "ok", "imported": counts})