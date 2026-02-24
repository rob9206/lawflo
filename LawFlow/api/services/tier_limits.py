"""Subscription tier limits and usage tracking."""

from datetime import datetime, timezone

from api.errors import ForbiddenError
from api.models.assessment import Assessment
from api.models.document import Document
from api.models.review import SpacedRepetitionCard
from api.models.session import StudySession


FREE_TIER_LIMITS = {
    "tutor_sessions_daily": 5,
    "document_uploads_total": 10,
    "exam_generations_daily": 3,
    "flashcard_generations_daily": 20,
    "auto_teach_sessions_daily": 3,
}


def _day_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)


def get_usage_snapshot(db, user_id: str) -> dict:
    day_start = _day_start_utc()
    tutor_sessions_daily = (
        db.query(StudySession)
        .filter(
            StudySession.user_id == user_id,
            StudySession.session_type == "tutor",
            StudySession.created_at >= day_start,
        )
        .count()
    )
    auto_teach_sessions_daily = (
        db.query(StudySession)
        .filter(
            StudySession.user_id == user_id,
            StudySession.session_type == "auto_teach",
            StudySession.created_at >= day_start,
        )
        .count()
    )
    document_uploads_total = db.query(Document).filter(Document.user_id == user_id).count()
    exam_generations_daily = (
        db.query(Assessment)
        .filter(
            Assessment.user_id == user_id,
            Assessment.created_at >= day_start,
        )
        .count()
    )
    flashcard_generations_daily = (
        db.query(SpacedRepetitionCard)
        .filter(
            SpacedRepetitionCard.user_id == user_id,
            SpacedRepetitionCard.created_at >= day_start,
        )
        .count()
    )
    return {
        "tutor_sessions_daily": tutor_sessions_daily,
        "document_uploads_total": document_uploads_total,
        "exam_generations_daily": exam_generations_daily,
        "flashcard_generations_daily": flashcard_generations_daily,
        "auto_teach_sessions_daily": auto_teach_sessions_daily,
    }


def _feature_display_name(feature: str) -> str:
    names = {
        "tutor_sessions_daily": "daily tutor sessions",
        "document_uploads_total": "total document uploads",
        "exam_generations_daily": "daily exam generations",
        "flashcard_generations_daily": "daily flashcard generations",
        "auto_teach_sessions_daily": "daily AutoTeach sessions",
    }
    return names.get(feature, feature)


def check_tier_limit(db, user, feature: str, increment: int = 1) -> None:
    tier = (user.tier or "free").lower()
    if tier == "pro":
        return

    if feature not in FREE_TIER_LIMITS:
        return

    usage = get_usage_snapshot(db, user.id)
    limit = FREE_TIER_LIMITS[feature]
    current = usage.get(feature, 0)
    if current + increment > limit:
        raise ForbiddenError(
            f"Free tier limit reached for {_feature_display_name(feature)} "
            f"({current}/{limit}). Upgrade to Pro to continue."
        )


def get_tier_status(db, user) -> dict:
    tier = (user.tier or "free").lower()
    usage = get_usage_snapshot(db, user.id)
    limits = FREE_TIER_LIMITS if tier != "pro" else {}
    return {
        "tier": tier,
        "subscription_status": user.subscription_status or "none",
        "usage": usage,
        "limits": limits,
    }
