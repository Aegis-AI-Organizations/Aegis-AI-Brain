import logging
from html import escape
from urllib.parse import urlencode

from config.config import (
    FRONTEND_BASE_URL,
    ONBOARDING_EMAIL_ENABLED,
)
from services.email_service import EmailService, create_email_service

logger = logging.getLogger(__name__)


def _build_action_url(path: str, token: str) -> str:
    base_url = FRONTEND_BASE_URL.rstrip("/")
    query = urlencode({"token": token})
    return f"{base_url}{path}?{query}"


def build_register_url(invitation_token: str) -> str:
    return _build_action_url("/register", invitation_token)


def build_setup_password_url(invitation_token: str) -> str:
    return build_register_url(invitation_token)


def _build_email_parts(
    *,
    recipient_name: str,
    company_name: str,
    action_url: str,
    action_label: str,
    intro_sentence: str,
    body_sentence: str,
    security_note: str,
    closing_line: str = "L'équipe Aegis AI",
) -> tuple[str, str]:
    safe_recipient_name = escape(recipient_name)
    safe_company_name = escape(company_name)
    safe_action_url = escape(action_url, quote=True)
    safe_action_label = escape(action_label)
    safe_intro_sentence = escape(intro_sentence)
    safe_body_sentence = escape(body_sentence)
    safe_security_note = escape(security_note)
    safe_closing_line = escape(closing_line)

    text_body = "\n".join(
        [
            f"Bonjour {recipient_name},",
            "",
            safe_intro_sentence,
            "",
            safe_body_sentence,
            action_url,
            "",
            safe_security_note,
            "",
            safe_closing_line,
        ]
    )

    html_body = f"""
<html>
  <body style="margin:0;background:#f5f7fb;padding:0;">
    <div style="background:#f5f7fb;padding:32px 16px;font-family:Inter,Arial,sans-serif;color:#111827;">
      <div style="max-width:640px;margin:0 auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:20px;overflow:hidden;">
        <div style="padding:32px 28px 12px 28px;border-bottom:1px solid #eef2f7;">
          <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;font-weight:700;color:#2563eb;margin-bottom:12px;">Aegis AI</div>
          <h1 style="margin:0 0 16px 0;font-size:28px;line-height:1.2;color:#0f172a;">Bonjour {safe_recipient_name},</h1>
          <p style="margin:0 0 12px 0;font-size:16px;line-height:1.7;color:#334155;">{safe_intro_sentence}</p>
          <p style="margin:0 0 24px 0;font-size:16px;line-height:1.7;color:#334155;">{safe_body_sentence}</p>
          <div style="margin:0 0 24px 0;">
            <a href="{safe_action_url}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;padding:14px 22px;border-radius:999px;font-weight:700;font-size:15px;line-height:1;">{safe_action_label}</a>
          </div>
          <p style="margin:0 0 12px 0;font-size:14px;line-height:1.6;color:#475569;">{safe_security_note}</p>
        </div>
        <div style="padding:20px 28px 28px 28px;background:#f8fafc;">
          <p style="margin:0;font-size:13px;line-height:1.6;color:#64748b;">{safe_closing_line}</p>
          <p style="margin:8px 0 0 0;font-size:13px;line-height:1.6;color:#64748b;">{safe_company_name}</p>
        </div>
      </div>
    </div>
  </body>
</html>
""".strip()

    return text_body, html_body


def render_onboarding_invitation_email(
    *,
    owner_name: str,
    company_name: str,
    invitation_token: str,
) -> tuple[str, str, str]:
    action_url = build_register_url(invitation_token)
    intro_sentence = f"Votre espace Aegis AI pour {company_name} est prêt."
    body_sentence = (
        "Cliquez sur le bouton ci-dessous pour créer votre mot de passe "
        "et finaliser votre première connexion."
    )
    security_note = "Ce lien est temporaire, à usage unique, et ne doit pas être partagé."
    text_body, html_body = _build_email_parts(
        recipient_name=owner_name,
        company_name=company_name,
        action_url=action_url,
        action_label="Activer mon accès",
        intro_sentence=intro_sentence,
        body_sentence=body_sentence,
        security_note=security_note,
    )
    return "Activez votre compte Aegis AI", html_body, text_body


def render_access_renewal_email(
    *,
    owner_name: str,
    company_name: str,
    renewal_token: str,
) -> tuple[str, str, str]:
    action_url = build_register_url(renewal_token)
    intro_sentence = f"Votre accès Aegis AI pour {company_name} doit être renouvelé."
    body_sentence = (
        "Utilisez le lien ci-dessous pour restaurer votre accès et créer un "
        "nouveau mot de passe."
    )
    security_note = "Ce lien est temporaire, à usage unique, et expire automatiquement."
    text_body, html_body = _build_email_parts(
        recipient_name=owner_name,
        company_name=company_name,
        action_url=action_url,
        action_label="Renouveler mon accès",
        intro_sentence=intro_sentence,
        body_sentence=body_sentence,
        security_note=security_note,
    )
    return "Renouvelez votre accès Aegis AI", html_body, text_body


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

    subject, html_body, text_body = render_onboarding_invitation_email(
        owner_name=owner_name,
        company_name=company_name,
        invitation_token=invitation_token,
    )

    service = email_service or create_email_service()
    service.send_email(
        to=owner_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )

    logger.info("Onboarding invitation email sent to %s", owner_email)
    return True


def send_access_renewal_email(
    *,
    owner_email: str,
    owner_name: str,
    company_name: str,
    renewal_token: str,
    email_service: EmailService | None = None,
) -> bool:
    if not ONBOARDING_EMAIL_ENABLED:
        logger.info("Onboarding email disabled; skipping renewal email")
        return False

    subject, html_body, text_body = render_access_renewal_email(
        owner_name=owner_name,
        company_name=company_name,
        renewal_token=renewal_token,
    )

    service = email_service or create_email_service()
    service.send_email(
        to=owner_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )

    logger.info("Access renewal email sent to %s", owner_email)
    return True
