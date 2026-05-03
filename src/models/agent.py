from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, String, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.company import Company

class Agent(Base):
    """Agent model mapped to the 'agents' table."""

    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), server_default=text("'IDLE'"), default="IDLE"
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        default=lambda: datetime.now(timezone.utc),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        default=lambda: datetime.now(timezone.utc),
    )

    company: Mapped[Company] = relationship("Company", back_populates="agents")

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, status={self.status})>"
