import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode

from config.config import (
    FRONTEND_BASE_URL,
    ONBOARDING_EMAIL_ENABLED,
    SMTP_FROM_EMAIL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_USE_TLS,
)

logger = logging.getLogger(__name__)


def build_setup_password_url(invitation_token: str) -> str:
    base_url = FRONTEND_BASE_URL.rstrip("/")
    query = urlencode({"token": invitation_token})
    return f"{base_url}/setup-password?{query}"


def send_onboarding_invitation_email(
    *,
    owner_email: str,
    owner_name: str,
    company_name: str,
    invitation_token: str,
) -> bool:
    if not ONBOARDING_EMAIL_ENABLED:
        logger.info("Onboarding email disabled; skipping invitation email")
        return False

    setup_url = build_setup_password_url(invitation_token)
    message = EmailMessage()
    message["Subject"] = "Activez votre compte Aegis AI"
    message["From"] = SMTP_FROM_EMAIL
    message["To"] = owner_email
    message.set_content(
        "\n".join(
            [
                f"Bonjour {owner_name},",
                "",
                f"Votre espace Aegis AI pour {company_name} est prêt.",
                "Définissez votre mot de passe pour finaliser votre première connexion :",
                setup_url,
                "",
                "Ce lien est temporaire et ne doit pas être partagé.",
                "",
                "L'équipe Aegis AI",
            ]
        )
    )

    if SMTP_USE_TLS:
        smtp = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10)
    else:
        smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)

    with smtp:
        if SMTP_USERNAME:
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(message)

    logger.info("Onboarding invitation email sent to %s", owner_email)
    return True
