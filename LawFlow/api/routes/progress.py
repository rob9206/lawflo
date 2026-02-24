"""Progress and mastery tracking routes."""

from datetime import datetime, timezone, timedelta

from flask import Blueprint, jsonify, request

from api.middleware.auth import get_current_user_id, login_required
from api.services.database import get_db
from api.models.student import SubjectMastery, TopicMastery
from api.models.session import StudySession
from api.models.document import KnowledgeChunk

bp = Blueprint("progress", __name__, url_prefix="/api/progress")


@bp.before_request
@login_required
def require_auth():
    return None


@bp.route("/dashboard", methods=["GET"])
def dashboard():
    """Full dashboard data: subjects, mastery, study time, knowledge stats."""
    user_id = get_current_user_id()
    with get_db() as db:
        subjects = (
            db.query(SubjectMastery)
            .filter_by(user_id=user_id)
            .order_by(SubjectMastery.display_name)
            .all()
        )
        total_chunks = db.query(KnowledgeChunk).filter_by(user_id=user_id).count()
        total_sessions = db.query(StudySession).filter_by(user_id=user_id).count()
        total_study_minutes = sum(s.total_study_time_minutes or 0 for s in subjects)

        subject_data = []
        for s in subjects:
            topics = db.query(TopicMastery).filter_by(user_id=user_id, subject=s.subject).all()
            subject_data.append({
                **s.to_dict(),
                "topic_count": len(topics),
                "topics": [t.to_dict() for t in topics],
            })

        return jsonify({
            "subjects": subject_data,
            "stats": {
                "total_subjects": len(subjects),
                "total_knowledge_chunks": total_chunks,
                "total_sessions": total_sessions,
                "total_study_minutes": total_study_minutes,
                "overall_mastery": (
                    sum(s.mastery_score for s in subjects) / len(subjects)
                    if subjects else 0
                ),
            },
        })


@bp.route("/mastery", methods=["GET"])
def mastery_overview():
    """Mastery scores by subject."""
    user_id = get_current_user_id()
    with get_db() as db:
        subjects = (
            db.query(SubjectMastery)
            .filter_by(user_id=user_id)
            .order_by(SubjectMastery.mastery_score)
            .all()
        )
        return jsonify([s.to_dict() for s in subjects])


@bp.route("/mastery/<subject>", methods=["GET"])
def subject_mastery(subject: str):
    """Detailed mastery for a specific subject with topic breakdown."""
    user_id = get_current_user_id()
    with get_db() as db:
        subj = db.query(SubjectMastery).filter_by(user_id=user_id, subject=subject).first()
        if not subj:
            return jsonify({"error": "Subject not found"}), 404

        topics = (
            db.query(TopicMastery)
            .filter_by(user_id=user_id, subject=subject)
            .order_by(TopicMastery.mastery_score)
            .all()
        )

        return jsonify({
            **subj.to_dict(),
            "topics": [t.to_dict() for t in topics],
        })


@bp.route("/weaknesses", methods=["GET"])
def weaknesses():
    """Top weakest topics across all subjects."""
    limit = request.args.get("limit", 10, type=int)
    user_id = get_current_user_id()
    with get_db() as db:
        topics = (
            db.query(TopicMastery)
            .filter(TopicMastery.user_id == user_id)
            .filter(TopicMastery.exposure_count > 0)
            .order_by(TopicMastery.mastery_score)
            .limit(limit)
            .all()
        )
        return jsonify([t.to_dict() for t in topics])


@bp.route("/history", methods=["GET"])
def study_history():
    """Daily study minutes and session counts for the past N days."""
    days = request.args.get("days", 30, type=int)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    user_id = get_current_user_id()
    with get_db() as db:
        sessions = (
            db.query(StudySession)
            .filter(StudySession.user_id == user_id)
            .filter(StudySession.started_at >= cutoff)
            .order_by(StudySession.started_at)
            .all()
        )

        # Aggregate by date (UTC)
        daily: dict[str, dict] = {}
        for session in sessions:
            day = session.started_at.strftime("%Y-%m-%d")
            if day not in daily:
                daily[day] = {"date": day, "minutes": 0, "sessions": 0}
            daily[day]["minutes"] += session.duration_minutes or 0
            daily[day]["sessions"] += 1

        # Fill in zero-days so charts are continuous
        result = []
        for i in range(days):
            d = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            result.append(daily.get(d, {"date": d, "minutes": 0, "sessions": 0}))

        return jsonify(result)


@bp.route("/streaks", methods=["GET"])
def streaks():
    """Current streak, longest streak, and total study days."""
    user_id = get_current_user_id()
    with get_db() as db:
        sessions = (
            db.query(StudySession)
            .filter(StudySession.user_id == user_id)
            .order_by(StudySession.started_at.desc())
            .all()
        )

    if not sessions:
        return jsonify({"current_streak": 0, "longest_streak": 0, "total_days": 0})

    # Collect unique study dates (UTC date strings)
    study_dates = sorted(
        {s.started_at.strftime("%Y-%m-%d") for s in sessions},
        reverse=True,
    )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    # Current streak — count from today or yesterday backwards
    current_streak = 0
    if study_dates and study_dates[0] in (today, yesterday):
        check = datetime.now(timezone.utc).date() if study_dates[0] == today else (datetime.now(timezone.utc) - timedelta(days=1)).date()
        for date_str in study_dates:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            if d == check:
                current_streak += 1
                check -= timedelta(days=1)
            elif d < check:
                break

    # Longest streak
    longest = 0
    run = 1
    dates_asc = sorted(study_dates)
    for i in range(1, len(dates_asc)):
        prev = datetime.strptime(dates_asc[i - 1], "%Y-%m-%d").date()
        curr = datetime.strptime(dates_asc[i], "%Y-%m-%d").date()
        if (curr - prev).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    longest = max(longest, run)

    return jsonify({
        "current_streak": current_streak,
        "longest_streak": longest,
        "total_days": len(study_dates),
    })
