from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional

from sqlalchemy import ForeignKey, String, DateTime, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class TokenLedger(Base):
    """TokenLedger model mapped to the 'token_ledger' table."""

    __tablename__ = "token_ledger"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    scan_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("scans.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<TokenLedger(company_id={self.company_id}, amount={self.amount}, reason={self.reason!r})>"
