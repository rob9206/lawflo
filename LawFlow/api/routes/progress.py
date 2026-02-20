"""Progress and mastery tracking routes."""

from flask import Blueprint, jsonify, request

from api.services.database import get_db
from api.models.student import SubjectMastery, TopicMastery
from api.models.session import StudySession
from api.models.document import KnowledgeChunk

bp = Blueprint("progress", __name__, url_prefix="/api/progress")


@bp.route("/dashboard", methods=["GET"])
def dashboard():
    """Full dashboard data: subjects, mastery, study time, knowledge stats."""
    with get_db() as db:
        subjects = db.query(SubjectMastery).order_by(SubjectMastery.display_name).all()
        total_chunks = db.query(KnowledgeChunk).count()
        total_sessions = db.query(StudySession).count()
        total_study_minutes = sum(s.total_study_time_minutes or 0 for s in subjects)

        subject_data = []
        for s in subjects:
            topics = db.query(TopicMastery).filter_by(subject=s.subject).all()
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
    with get_db() as db:
        subjects = db.query(SubjectMastery).order_by(SubjectMastery.mastery_score).all()
        return jsonify([s.to_dict() for s in subjects])


@bp.route("/mastery/<subject>", methods=["GET"])
def subject_mastery(subject: str):
    """Detailed mastery for a specific subject with topic breakdown."""
    with get_db() as db:
        subj = db.query(SubjectMastery).filter_by(subject=subject).first()
        if not subj:
            return jsonify({"error": "Subject not found"}), 404

        topics = (
            db.query(TopicMastery)
            .filter_by(subject=subject)
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
    with get_db() as db:
        topics = (
            db.query(TopicMastery)
            .filter(TopicMastery.exposure_count > 0)
            .order_by(TopicMastery.mastery_score)
            .limit(limit)
            .all()
        )
        return jsonify([t.to_dict() for t in topics])
