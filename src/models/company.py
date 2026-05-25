from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Boolean, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.user import User
    from models.agent import Agent


class Company(Base):
    """Company model mapped to the 'companies' table."""

    __tablename__ = "companies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deployment_token: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_companies_owner_id_users",
        ),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), default=True
    )
    org_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    org_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    token_balance: Mapped[int] = mapped_column(server_default=text("0"), default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        default=lambda: datetime.now(timezone.utc),
    )

    owner: Mapped[Optional[User]] = relationship(
        "User", foreign_keys=[owner_id], back_populates="owned_company"
    )

    members: Mapped[List[User]] = relationship(
        "User", primaryjoin="Company.id == User.company_id", back_populates="company"
    )

    agents: Mapped[List[Agent]] = relationship(
        "Agent", back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Company(name={self.name!r}, is_active={self.is_active})>"
