"""Profile and settings routes."""

from flask import Blueprint, jsonify

from api.services.database import get_db, reset_database
from api.models.student import SubjectMastery, TopicMastery
from api.models.session import StudySession, SessionMessage
from api.models.document import Document
from api.models.assessment import Assessment, AssessmentQuestion
from api.models.study_plan import StudyPlan, PlanTask
from api.models.review import SpacedRepetitionCard
from api.models.exam_blueprint import ExamBlueprint, ExamTopicWeight

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