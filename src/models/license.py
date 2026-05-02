from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class License(Base):
    """License model mapped to the 'licenses' table."""

    __tablename__ = "licenses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    license_status: Mapped[str] = mapped_column(
        String(50), server_default=text("'active'"), default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<License(name={self.name!r}, status={self.license_status})>"
