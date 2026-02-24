"""User account and subscription model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

from api.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, default="Law Student")
    avatar_url = Column(String)

    # Subscription / billing fields
    tier = Column(String, default="free")  # free | pro
    stripe_customer_id = Column(String, unique=True)
    stripe_subscription_id = Column(String)
    subscription_status = Column(String, default="none")  # none | active | past_due | canceled

    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "tier": self.tier,
            "subscription_status": self.subscription_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
