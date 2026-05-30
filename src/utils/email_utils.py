import logging
from urllib.parse import urlencode

from config.config import (
    FRONTEND_BASE_URL,
    ONBOARDING_EMAIL_ENABLED,
)
from services.email_service import EmailService, create_email_service

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
    email_service: EmailService | None = None,
) -> bool:
    if not ONBOARDING_EMAIL_ENABLED:
        logger.info("Onboarding email disabled; skipping invitation email")
        return False

    setup_url = build_setup_password_url(invitation_token)
    text_body = "\n".join(
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
    html_body = "\n".join(
        [
            "<p>Bonjour {owner_name},</p>".format(owner_name=owner_name),
            f"<p>Votre espace Aegis AI pour <strong>{company_name}</strong> est prêt.</p>",
            "<p>Définissez votre mot de passe pour finaliser votre première connexion :</p>",
            f'<p><a href="{setup_url}">{setup_url}</a></p>',
            "<p>Ce lien est temporaire et ne doit pas être partagé.</p>",
            "<p>L'équipe Aegis AI</p>",
        ]
    )

    service = email_service or create_email_service()
    service.send_email(
        to=owner_email,
        subject="Activez votre compte Aegis AI",
        html_body=html_body,
        text_body=text_body,
    )

    logger.info("Onboarding invitation email sent to %s", owner_email)
    return True
