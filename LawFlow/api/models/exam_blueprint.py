"""ExamBlueprint — stores Claude's analysis of what a past exam tests.

When a student uploads a past exam, the ExamAnalyzer service sends it to Claude
to extract: which topics are tested, how heavily weighted, what format (essay/MC),
and common patterns. This data drives the AutoTeach priority engine.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from api.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ExamBlueprint(Base):
    """Top-level exam analysis — one per uploaded exam document."""
    __tablename__ = "exam_blueprints"
    __table_args__ = (
        Index("idx_eb_user", "user_id"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String, nullable=False)
    exam_title = Column(String)  # e.g. "Contracts Final Fall 2024"
    exam_format = Column(String)  # essay, mc, mixed, issue_spot
    total_questions = Column(Integer)
    time_limit_minutes = Column(Integer)
    professor_patterns = Column(Text)  # AI-detected patterns/tendencies
    high_yield_summary = Column(Text)  # "If you study nothing else, know these..."
    created_at = Column(DateTime, default=_now)

    topics_tested = relationship("ExamTopicWeight", back_populates="blueprint", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "subject": self.subject,
            "exam_title": self.exam_title,
            "exam_format": self.exam_format,
            "total_questions": self.total_questions,
            "time_limit_minutes": self.time_limit_minutes,
            "professor_patterns": self.professor_patterns,
            "high_yield_summary": self.high_yield_summary,
            "topics_tested": [t.to_dict() for t in self.topics_tested],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ExamTopicWeight(Base):
    """How heavily a specific topic is tested on a given exam."""
    __tablename__ = "exam_topic_weights"
    __table_args__ = (
        Index("idx_etw_user", "user_id"),
        Index("idx_etw_subject_topic", "user_id", "subject", "topic"),
        Index("idx_etw_blueprint", "blueprint_id"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    blueprint_id = Column(String, ForeignKey("exam_blueprints.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    weight = Column(Float, nullable=False)  # 0.0-1.0, how much of the exam covers this topic
    question_format = Column(String)  # essay, mc, issue_spot, short_answer
    difficulty = Column(Integer, default=50)  # 0-100
    notes = Column(Text)  # AI notes about how this topic tends to be tested
    created_at = Column(DateTime, default=_now)

    blueprint = relationship("ExamBlueprint", back_populates="topics_tested")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "blueprint_id": self.blueprint_id,
            "subject": self.subject,
            "topic": self.topic,
            "weight": self.weight,
            "question_format": self.question_format,
            "difficulty": self.difficulty,
            "notes": self.notes,
        }
