from unittest.mock import MagicMock, patch

from utils.email_utils import build_setup_password_url, send_onboarding_invitation_email


def test_build_setup_password_url():
    assert (
        build_setup_password_url("aegis_inv_token+with spaces")
        == "http://localhost/setup-password?token=aegis_inv_token%2Bwith+spaces"
    )


def test_send_onboarding_invitation_email_disabled():
    with patch("utils.email_utils.ONBOARDING_EMAIL_ENABLED", False), patch(
        "utils.email_utils.smtplib.SMTP"
    ) as mock_smtp:
        sent = send_onboarding_invitation_email(
            owner_email="owner@test.com",
            owner_name="Owner",
            company_name="Acme",
            invitation_token="aegis_inv_token",
        )

    assert sent is False
    mock_smtp.assert_not_called()


def test_send_onboarding_invitation_email_to_smtp():
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp

    with patch("utils.email_utils.ONBOARDING_EMAIL_ENABLED", True), patch(
        "utils.email_utils.SMTP_HOST", "mailpit"
    ), patch("utils.email_utils.SMTP_PORT", 1025), patch(
        "utils.email_utils.smtplib.SMTP", return_value=smtp
    ) as mock_smtp:
        sent = send_onboarding_invitation_email(
            owner_email="owner@test.com",
            owner_name="Owner",
            company_name="Acme",
            invitation_token="aegis_inv_token",
        )

    assert sent is True
    mock_smtp.assert_called_once_with("mailpit", 1025, timeout=10)
    smtp.send_message.assert_called_once()
    message = smtp.send_message.call_args.args[0]
    assert message["To"] == "owner@test.com"
    assert "http://localhost/setup-password?token=aegis_inv_token" in message.get_content()
