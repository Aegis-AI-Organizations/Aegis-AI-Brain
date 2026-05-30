import json
from unittest.mock import MagicMock, patch

import pytest

from services.email_service import (
    MailpitEmailService,
    ProductionEmailService,
    create_email_service,
)
from utils.email_utils import build_setup_password_url, send_onboarding_invitation_email


def test_build_setup_password_url():
    assert (
        build_setup_password_url("aegis_inv_token+with spaces")
        == "http://localhost/setup-password?token=aegis_inv_token%2Bwith+spaces"
    )


def test_send_onboarding_invitation_email_disabled():
    fake_service = MagicMock()

    with patch("utils.email_utils.ONBOARDING_EMAIL_ENABLED", False):
        sent = send_onboarding_invitation_email(
            owner_email="owner@test.com",
            owner_name="Owner",
            company_name="Acme",
            invitation_token="aegis_inv_token",
            email_service=fake_service,
        )

    assert sent is False
    fake_service.send_email.assert_not_called()


def test_send_onboarding_invitation_email_uses_injected_service():
    fake_service = MagicMock()

    with patch("utils.email_utils.ONBOARDING_EMAIL_ENABLED", True):
        sent = send_onboarding_invitation_email(
            owner_email="owner@test.com",
            owner_name="Owner",
            company_name="Acme",
            invitation_token="aegis_inv_token",
            email_service=fake_service,
        )

    assert sent is True
    fake_service.send_email.assert_called_once()
    call = fake_service.send_email.call_args.kwargs
    assert call["to"] == "owner@test.com"
    assert call["subject"] == "Activez votre compte Aegis AI"
    assert "setup-password?token=aegis_inv_token" in call["text_body"]
    assert "setup-password?token=aegis_inv_token" in call["html_body"]


def test_create_email_service_uses_mailpit_outside_production():
    service = create_email_service(env="dev")
    assert isinstance(service, MailpitEmailService)
    assert service.host == "localhost"
    assert service.port == 1025


def test_create_email_service_uses_production_in_production():
    with patch("services.email_service.AEGIS_EMAIL_API_KEY", "secret-key"):
        service = create_email_service(env="production")

    assert isinstance(service, ProductionEmailService)
    assert service.api_key == "secret-key"


def test_mailpit_email_service_sends_plain_smtp_message():
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp

    with patch("services.email_service.smtplib.SMTP", return_value=smtp) as mock_smtp:
        service = MailpitEmailService()
        sent = service.send_email(
            to="owner@test.com",
            subject="Hello",
            html_body="<p>Hello</p>",
            text_body="Hello",
        )

    assert sent is True
    mock_smtp.assert_called_once_with("localhost", 1025, timeout=10)
    smtp.send_message.assert_called_once()
    message = smtp.send_message.call_args.args[0]
    assert message["From"] == "Aegis AI Team <team@aegis-ai.fr>"
    assert message["To"] == "owner@test.com"
    assert message["Subject"] == "Hello"


def test_production_email_service_posts_to_api():
    response = MagicMock()
    response.__enter__.return_value = response
    response.status = 200
    response.getcode.return_value = 200

    with patch("services.email_service.urlopen", return_value=response) as mock_urlopen:
        service = ProductionEmailService(
            api_key="re_secret",
            api_url="https://api.resend.com/emails",
        )
        sent = service.send_email(
            to="owner@test.com",
            subject="Hello",
            html_body="<p>Hello</p>",
            text_body="Hello",
        )

    assert sent is True
    request = mock_urlopen.call_args.args[0]
    assert request.full_url == "https://api.resend.com/emails"
    assert request.get_header("Authorization") == "Bearer re_secret"
    body = json.loads(request.data.decode("utf-8"))
    assert body["from"] == "Aegis AI Team <team@aegis-ai.fr>"
    assert body["to"] == ["owner@test.com"]
    assert body["subject"] == "Hello"
    assert body["html"] == "<p>Hello</p>"
    assert body["text"] == "Hello"


def test_production_email_service_requires_api_key():
    service = ProductionEmailService(api_key="")

    with pytest.raises(RuntimeError, match="AEGIS_EMAIL_API_KEY"):
        service.send_email(
            to="owner@test.com",
            subject="Hello",
            html_body="<p>Hello</p>",
            text_body="Hello",
        )
