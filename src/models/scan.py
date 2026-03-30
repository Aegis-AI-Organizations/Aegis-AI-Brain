from __future__ import annotations
from datetime import datetime
from uuid import UUID, uuid4
from typing import List, Optional, Any

from sqlalchemy import ForeignKey, String, DateTime, text, LargeBinary, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base


class Scan(Base):
    """Scan model mapped to the 'scans' table."""

    __tablename__ = "scans"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    temporal_workflow_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    target_image: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), server_default=text("'PENDING'"), default="PENDING"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        default=datetime.utcnow,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    report_pdf: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)

    vulnerabilities: Mapped[List[Vulnerability]] = relationship(
        "Vulnerability", back_populates="scan", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Scan(workflow_id={self.temporal_workflow_id!r}, status={self.status})>"
        )


class Vulnerability(Base):
    """Vulnerability model mapped to the 'vulnerabilities' table."""

    __tablename__ = "vulnerabilities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    scan_id: Mapped[UUID] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    vuln_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    target_endpoint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        default=datetime.utcnow,
    )

    scan: Mapped[Scan] = relationship("Scan", back_populates="vulnerabilities")
    evidences: Mapped[List[Evidence]] = relationship(
        "Evidence", back_populates="vulnerability", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Vulnerability(type={self.vuln_type!r}, severity={self.severity})>"


class Evidence(Base):
    """Evidence model mapped to the 'evidences' table."""

    __tablename__ = "evidences"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vulnerability_id: Mapped[UUID] = mapped_column(
        ForeignKey("vulnerabilities.id", ondelete="CASCADE"), nullable=False
    )
    payload_used: Mapped[str] = mapped_column(Text, nullable=False)
    loot_data: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        default=datetime.utcnow,
    )

    vulnerability: Mapped[Vulnerability] = relationship(
        "Vulnerability", back_populates="evidences"
    )

    def __repr__(self) -> str:
        return f"<Evidence(vulnerability_id={self.vulnerability_id})>"
