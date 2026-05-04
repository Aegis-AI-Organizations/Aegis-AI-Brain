from __future__ import annotations
import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Boolean, DateTime, text, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.company import Company
    from models.refresh_token import RefreshToken


class UserRole(str, enum.Enum):
    """User roles matching the PostgreSQL Enum 'user_role'."""

    superadmin = "superadmin"
    admin = "admin"
    billing_aegis = "billing_aegis"
    technicien = "technicien"
    support = "support"
    commercial = "commercial"
    owner = "owner"
    billing_client = "billing_client"
    operateur = "operateur"
    viewer = "viewer"


class UserActivationStatus(str, enum.Enum):
    """Lifecycle status for user account activation."""

    active = "active"
    pending_activation = "pending_activation"


class User(Base):
    """User model mapped to the 'users' table."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True),
        server_default=text("'viewer'"),
        default=UserRole.viewer,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), default=True
    )
    activation_status: Mapped[UserActivationStatus] = mapped_column(
        Enum(UserActivationStatus, name="user_activation_status", native_enum=True),
        server_default=text("'active'"),
        default=UserActivationStatus.active,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        default=lambda: datetime.now(timezone.utc),
    )

    company: Mapped[Optional[Company]] = relationship(
        "Company", foreign_keys=[company_id], back_populates="members"
    )
    owned_company: Mapped[Optional[Company]] = relationship(
        "Company",
        primaryjoin="User.id == Company.owner_id",
        back_populates="owner",
        uselist=False,
    )
    refresh_tokens: Mapped[List[RefreshToken]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(email={self.email!r}, role={self.role})>"
