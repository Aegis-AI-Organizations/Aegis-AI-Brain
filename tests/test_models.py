import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import (
    Base,
    Company,
    User,
    UserRole,
    RefreshToken,
    License,
    Scan,
    Vulnerability,
    Evidence,
)
from datetime import datetime, timedelta, UTC
import uuid


@pytest.fixture
def db_session():
    """In-memory SQLite session for testing models."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_company_creation(db_session: Session):
    """Tests the Company model creation and its basic fields."""
    name = "Test Corporation"
    logo = "https://example.com/logo.png"

    company = Company(name=name, logo_url=logo)
    db_session.add(company)
    db_session.commit()

    assert company.id is not None
    assert isinstance(company.id, uuid.UUID)
    assert company.name == name
    assert company.logo_url == logo
    assert company.is_active is True
    assert isinstance(company.created_at, datetime)


def test_user_creation_and_role_enum(db_session: Session):
    """Tests the User model, including the role enum and default fields."""
    email = "admin@example.com"
    pwd_hash = "mock_hash_123"

    user = User(email=email, password_hash=pwd_hash, role=UserRole.superadmin)
    db_session.add(user)
    db_session.commit()

    assert user.id is not None
    assert user.email == email
    assert user.password_hash == pwd_hash
    assert user.role == UserRole.superadmin
    assert user.is_active is True


def test_company_user_relationships(db_session: Session):
    """Tests complex relationships between companies and users (owner/members)."""
    owner = User(email="owner@test.com", password_hash="hash", role=UserRole.owner)
    db_session.add(owner)
    db_session.commit()

    company = Company(name="Linked Corp", owner_id=owner.id)
    db_session.add(company)
    db_session.commit()

    owner.company_id = company.id

    member = User(
        email="member@test.com",
        password_hash="hash",
        role=UserRole.viewer,
        company_id=company.id,
    )
    db_session.add(member)

    db_session.commit()

    db_session.refresh(company)
    db_session.refresh(owner)

    assert company.owner_id == owner.id
    assert owner.owned_company == company

    assert len(company.members) == 2
    assert owner in company.members
    assert member in company.members


def test_refresh_token(db_session: Session):
    """Tests the RefreshToken model and its relationship to a user."""
    user = User(email="user@test.com", password_hash="hash")
    expires = datetime.now(UTC) + timedelta(days=7)
    token = RefreshToken(user=user, token_hash="token_hash_abc", expires_at=expires)

    db_session.add_all([user, token])
    db_session.commit()

    assert token.user_id == user.id
    assert token.user == user
    assert user.refresh_tokens == [token]
    assert token.revoked is False


def test_scan_vulnerability_evidence_chain(db_session: Session):
    """Tests the full chain of scans, vulnerabilities, and evidences."""
    scan = Scan(temporal_workflow_id="wf-99", target_image="vuln-app:latest")

    vuln = Vulnerability(
        scan=scan, vuln_type="XSS", severity="MEDIUM", description="Reflected XSS found"
    )

    evidence = Evidence(
        vulnerability=vuln,
        payload_used="<script>alert(1)</script>",
        loot_data={"found": True},
    )

    db_session.add_all([scan, vuln, evidence])
    db_session.commit()

    assert len(scan.vulnerabilities) == 1
    assert scan.vulnerabilities[0] == vuln

    assert len(vuln.evidences) == 1
    assert vuln.evidences[0] == evidence
    assert evidence.vulnerability == vuln

    assert evidence.loot_data == {"found": True}
    assert vuln.scan_id == scan.id


def test_license_model(db_session: Session):
    """Tests the basic License model."""
    license_name = "Enterprise v1"
    lic = License(name=license_name)

    db_session.add(lic)
    db_session.commit()

    assert lic.id is not None
    assert lic.name == license_name
    assert lic.license_status == "active"
