"""Assessment and question models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from api.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (
        Index("idx_asmt_user", "user_id"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    session_id = Column(String, ForeignKey("study_sessions.id"))
    assessment_type = Column(String, nullable=False)  # multiple_choice, essay, issue_spot, mixed
    subject = Column(String, nullable=False)
    topics = Column(Text)  # JSON array
    total_questions = Column(Integer, nullable=False)
    score = Column(Float)  # 0-100
    time_limit_minutes = Column(Integer)
    time_taken_minutes = Column(Float)
    is_timed = Column(Integer, default=0)
    feedback_summary = Column(Text)
    created_at = Column(DateTime, default=_now)
    completed_at = Column(DateTime)

    questions = relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "session_id": self.session_id,
            "assessment_type": self.assessment_type,
            "subject": self.subject,
            "topics": json.loads(self.topics) if self.topics else [],
            "total_questions": self.total_questions,
            "score": self.score,
            "time_limit_minutes": self.time_limit_minutes,
            "time_taken_minutes": self.time_taken_minutes,
            "is_timed": bool(self.is_timed),
            "feedback_summary": self.feedback_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"
    __table_args__ = (
        Index("idx_aq_user", "user_id"),
        Index("idx_aq_assessment", "assessment_id"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    assessment_id = Column(String, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    question_index = Column(Integer, nullable=False)
    question_type = Column(String, nullable=False)  # mc, essay, issue_spot
    question_text = Column(Text, nullable=False)
    options = Column(Text)  # JSON array for MC
    correct_answer = Column(Text)
    student_answer = Column(Text)
    is_correct = Column(Integer)  # 0/1 for MC, null for essay
    score = Column(Float)  # 0-100 for essay grading
    feedback = Column(Text)
    subject = Column(String)
    topic = Column(String)
    difficulty = Column(Integer, default=50)
    created_at = Column(DateTime, default=_now)

    assessment = relationship("Assessment", back_populates="questions")

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "assessment_id": self.assessment_id,
            "question_index": self.question_index,
            "question_type": self.question_type,
            "question_text": self.question_text,
            "options": json.loads(self.options) if self.options else None,
            "correct_answer": self.correct_answer,
            "student_answer": self.student_answer,
            "is_correct": bool(self.is_correct) if self.is_correct is not None else None,
            "score": self.score,
            "feedback": self.feedback,
            "subject": self.subject,
            "topic": self.topic,
            "difficulty": self.difficulty,
        }
