"""Study session and message models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from api.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class StudySession(Base):
    __tablename__ = "study_sessions"
    __table_args__ = (
        Index("idx_ss_user", "user_id"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    session_type = Column(String, nullable=False)  # tutor, assessment, review, free_study
    tutor_mode = Column(String)  # socratic, irac, issue_spot, hypo, explain, exam_strategy
    subject = Column(String)
    topics = Column(Text)  # JSON array
    started_at = Column(DateTime, nullable=False, default=_now)
    ended_at = Column(DateTime)
    duration_minutes = Column(Float)
    messages_count = Column(Integer, default=0)
    available_minutes = Column(Integer)  # student's time budget for this session
    performance_score = Column(Float)  # 0-100
    notes = Column(Text)
    created_at = Column(DateTime, default=_now)

    messages = relationship("SessionMessage", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "session_type": self.session_type,
            "tutor_mode": self.tutor_mode,
            "subject": self.subject,
            "topics": json.loads(self.topics) if self.topics else [],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_minutes": self.duration_minutes,
            "messages_count": self.messages_count,
            "available_minutes": self.available_minutes,
            "performance_score": self.performance_score,
            "notes": self.notes,
        }


class SessionMessage(Base):
    __tablename__ = "session_messages"
    __table_args__ = (
        Index("idx_sm_user", "user_id"),
        Index("idx_sm_session", "session_id"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    session_id = Column(String, ForeignKey("study_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    message_index = Column(Integer, nullable=False)
    metadata_json = Column(Text)  # JSON: topic tags, performance signals
    created_at = Column(DateTime, default=_now)

    session = relationship("StudySession", back_populates="messages")

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "message_index": self.message_index,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
