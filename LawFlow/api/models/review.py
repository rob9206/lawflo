"""Spaced repetition review card model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Index

from api.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SpacedRepetitionCard(Base):
    __tablename__ = "spaced_repetition_cards"
    __table_args__ = (
        Index("idx_src_user", "user_id"),
        Index("idx_src_review", "next_review"),
        Index("idx_src_subject", "user_id", "subject"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    chunk_id = Column(String, ForeignKey("knowledge_chunks.id"))
    subject = Column(String, nullable=False)
    topic = Column(String)
    front = Column(Text, nullable=False)  # Question/prompt
    back = Column(Text, nullable=False)  # Answer/explanation
    card_type = Column(String, default="concept")  # concept, rule, case_holding, element_list
    ease_factor = Column(Float, default=2.5)  # SM-2 algorithm
    interval_days = Column(Integer, default=1)
    repetitions = Column(Integer, default=0)
    next_review = Column(DateTime)
    last_reviewed = Column(DateTime)
    created_at = Column(DateTime, default=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "chunk_id": self.chunk_id,
            "subject": self.subject,
            "topic": self.topic,
            "front": self.front,
            "back": self.back,
            "card_type": self.card_type,
            "ease_factor": self.ease_factor,
            "interval_days": self.interval_days,
            "repetitions": self.repetitions,
            "next_review": self.next_review.isoformat() if self.next_review else None,
            "last_reviewed": self.last_reviewed.isoformat() if self.last_reviewed else None,
        }
