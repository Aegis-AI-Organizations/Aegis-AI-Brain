from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, String, DateTime, text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.user import User


class OnboardingInvitation(Base):
    """One-time token used to activate an onboarded owner account."""

    __tablename__ = "onboarding_invitations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped[User] = relationship("User", back_populates="onboarding_invitations")

    @hybrid_property
    def is_expired(self) -> bool:
        dt = self.expires_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > dt

    @hybrid_property
    def is_used(self) -> bool:
        return self.used_at is not None

    def __repr__(self) -> str:
        return f"<OnboardingInvitation(user_id={self.user_id}, used={self.is_used})>"
