"""Rewards system models — points ledger, achievements, and profile."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Index

from api.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PointLedger(Base):
    """Append-only transaction log. Every point earn is a row.
    Balance = SUM(amount). Full auditability."""

    __tablename__ = "point_ledger"
    __table_args__ = (
        Index("idx_pl_user", "user_id"),
        Index("idx_pl_created", "created_at"),
        Index("idx_pl_activity", "activity_type"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    amount = Column(Integer, nullable=False)
    activity_type = Column(String, nullable=False)
    activity_id = Column(String)
    description = Column(String, nullable=False)
    bonus_type = Column(String)  # null, "streak", "random_bonus", "first_time"
    metadata_json = Column(Text)
    created_at = Column(DateTime, default=_now)

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "amount": self.amount,
            "activity_type": self.activity_type,
            "activity_id": self.activity_id,
            "description": self.description,
            "bonus_type": self.bonus_type,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Achievement(Base):
    """Persistent record of achievement progress and unlock state."""

    __tablename__ = "achievements"
    __table_args__ = (
        Index("idx_ach_user", "user_id"),
        Index("idx_ach_key", "user_id", "achievement_key", unique=True),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    achievement_key = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    icon = Column(String, default="trophy")
    rarity = Column(String, default="common")  # common/uncommon/rare/legendary
    points_awarded = Column(Integer, default=0)
    unlocked_at = Column(DateTime)
    target_value = Column(Integer, default=1)
    current_value = Column(Integer, default=0)
    created_at = Column(DateTime, default=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "achievement_key": self.achievement_key,
            "title": self.title,
            "description": self.description,
            "icon": self.icon,
            "rarity": self.rarity,
            "points_awarded": self.points_awarded,
            "unlocked": self.unlocked_at is not None,
            "unlocked_at": self.unlocked_at.isoformat() if self.unlocked_at else None,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "progress": min(self.current_value / self.target_value, 1.0) if self.target_value else 1.0,
        }


class RewardsProfile(Base):
    """Single-row profile for the student (no auth — one user)."""

    __tablename__ = "rewards_profile"
    __table_args__ = (
        Index("idx_rp_user", "user_id", unique=True),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    active_title = Column(String, default="Law Student")
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_active_date = Column(String)  # "2026-02-21" format
    total_earned = Column(Integer, default=0)
    level = Column(Integer, default=1)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "active_title": self.active_title,
            "current_streak": self.current_streak,
            "longest_streak": self.longest_streak,
            "last_active_date": self.last_active_date,
            "total_earned": self.total_earned,
            "level": self.level,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
