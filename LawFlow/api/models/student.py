"""Student mastery tracking models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index, UniqueConstraint

from api.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SubjectMastery(Base):
    __tablename__ = "subject_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "subject"),
        Index("idx_sm_user", "user_id"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    subject = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    mastery_score = Column(Float, default=0.0)  # 0-100
    total_study_time_minutes = Column(Integer, default=0)
    sessions_count = Column(Integer, default=0)
    assessments_count = Column(Integer, default=0)
    last_studied_at = Column(DateTime)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "display_name": self.display_name,
            "mastery_score": self.mastery_score,
            "total_study_time_minutes": self.total_study_time_minutes,
            "sessions_count": self.sessions_count,
            "assessments_count": self.assessments_count,
            "last_studied_at": self.last_studied_at.isoformat() if self.last_studied_at else None,
        }


class TopicMastery(Base):
    __tablename__ = "topic_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "subject", "topic"),
        Index("idx_tm_user", "user_id"),
        Index("idx_tm_subject", "user_id", "subject"),
        Index("idx_tm_score", "mastery_score"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    mastery_score = Column(Float, default=0.0)  # 0-100
    confidence = Column(Float, default=0.0)  # 0-100
    exposure_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    incorrect_count = Column(Integer, default=0)
    last_tested_at = Column(DateTime)
    last_studied_at = Column(DateTime)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "topic": self.topic,
            "display_name": self.display_name,
            "mastery_score": self.mastery_score,
            "confidence": self.confidence,
            "exposure_count": self.exposure_count,
            "correct_count": self.correct_count,
            "incorrect_count": self.incorrect_count,
            "last_tested_at": self.last_tested_at.isoformat() if self.last_tested_at else None,
            "last_studied_at": self.last_studied_at.isoformat() if self.last_studied_at else None,
        }
