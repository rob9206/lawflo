"""Study plan and task models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Date, ForeignKey, Index
from sqlalchemy.orm import relationship

from api.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class StudyPlan(Base):
    __tablename__ = "study_plans"
    __table_args__ = (
        Index("idx_sp_user", "user_id"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    name = Column(String, nullable=False)
    exam_date = Column(DateTime)
    subjects = Column(Text, nullable=False)  # JSON array
    weekly_hours = Column(Float, default=20.0)
    strategy_notes = Column(Text)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    tasks = relationship("PlanTask", back_populates="plan", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "name": self.name,
            "exam_date": self.exam_date.isoformat() if self.exam_date else None,
            "subjects": json.loads(self.subjects) if self.subjects else [],
            "weekly_hours": self.weekly_hours,
            "strategy_notes": self.strategy_notes,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PlanTask(Base):
    __tablename__ = "plan_tasks"
    __table_args__ = (
        Index("idx_pt_user", "user_id"),
        Index("idx_pt_plan", "plan_id"),
        Index("idx_pt_date", "scheduled_date"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    plan_id = Column(String, ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String, nullable=False)
    topic = Column(String)
    task_type = Column(String, nullable=False)  # study, practice, review, assessment
    description = Column(Text, nullable=False)
    scheduled_date = Column(Date, nullable=False)
    estimated_minutes = Column(Integer, default=30)
    priority = Column(Integer, default=50)  # 0-100
    is_completed = Column(Integer, default=0)
    completed_at = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=_now)

    plan = relationship("StudyPlan", back_populates="tasks")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "subject": self.subject,
            "topic": self.topic,
            "task_type": self.task_type,
            "description": self.description,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "estimated_minutes": self.estimated_minutes,
            "priority": self.priority,
            "is_completed": bool(self.is_completed),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
