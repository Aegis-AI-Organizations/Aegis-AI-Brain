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
    eyebrow: str,
    headline: str,
    subheadline: str,
    intro_sentence: str,
    body_sentence: str,
    security_note: str,
    closing_line: str = "L'équipe Aegis AI",
) -> tuple[str, str]:
    safe_recipient_name = escape(recipient_name)
    safe_company_name = escape(company_name)
    safe_action_url = escape(action_url, quote=True)
    safe_action_label = escape(action_label)
    safe_eyebrow = escape(eyebrow)
    safe_headline = escape(headline)
    safe_subheadline = escape(subheadline)
    safe_intro_sentence = escape(intro_sentence)
    safe_body_sentence = escape(body_sentence)
    safe_security_note = escape(security_note)
    safe_closing_line = escape(closing_line)

    text_body = "\n".join(
        [
            f"Bonjour {recipient_name},",
            "",
            eyebrow,
            "",
            headline,
            "",
            subheadline,
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
        <div style="padding:28px 28px 18px 28px;background:linear-gradient(135deg,#eff6ff 0%,#ffffff 55%,#ecfeff 100%);border-bottom:1px solid #e5e7eb;">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:18px;">
            <div style="width:44px;height:44px;border-radius:14px;background:linear-gradient(135deg,#2563eb 0%,#06b6d4 100%);color:#ffffff;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:18px;letter-spacing:.04em;">A</div>
            <div>
              <div style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;font-weight:800;color:#2563eb;">Aegis AI</div>
              <div style="font-size:13px;line-height:1.4;color:#64748b;">Secure access workflows</div>
            </div>
          </div>
          <div style="display:inline-block;padding:6px 12px;border-radius:999px;background:#dbeafe;color:#1d4ed8;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin-bottom:14px;">{safe_eyebrow}</div>
          <h1 style="margin:0 0 12px 0;font-size:30px;line-height:1.15;color:#0f172a;letter-spacing:-0.02em;">{safe_headline}</h1>
          <p style="margin:0 0 10px 0;font-size:17px;line-height:1.7;color:#0f172a;font-weight:600;">Bonjour {safe_recipient_name},</p>
          <p style="margin:0 0 12px 0;font-size:16px;line-height:1.7;color:#334155;">{safe_subheadline}</p>
          <p style="margin:0 0 12px 0;font-size:16px;line-height:1.7;color:#334155;">{safe_intro_sentence}</p>
          <p style="margin:0 0 22px 0;font-size:16px;line-height:1.7;color:#334155;">{safe_body_sentence}</p>
          <div style="margin:0 0 20px 0;">
            <a href="{safe_action_url}" style="display:inline-block;background:linear-gradient(135deg,#2563eb 0%,#1d4ed8 100%);color:#ffffff;text-decoration:none;padding:15px 24px;border-radius:999px;font-weight:800;font-size:15px;line-height:1;box-shadow:0 10px 24px rgba(37,99,235,.18);">{safe_action_label}</a>
          </div>
          <div style="padding:14px 16px;border-radius:16px;background:#f8fafc;border:1px solid #e2e8f0;">
            <p style="margin:0;font-size:14px;line-height:1.7;color:#475569;"><strong style="color:#0f172a;">Sécurité :</strong> {safe_security_note}</p>
          </div>
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
    security_note = (
        "Ce lien est temporaire, à usage unique, et ne doit pas être partagé."
    )
    text_body, html_body = _build_email_parts(
        recipient_name=owner_name,
        company_name=company_name,
        action_url=action_url,
        action_label="Activer mon accès",
        eyebrow="Invitation",
        headline="Activez votre compte Aegis AI",
        subheadline="Un espace d'entreprise sécurisé vient d'être préparé pour vous.",
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
        eyebrow="Renouvellement d'accès",
        headline="Restaurez votre accès Aegis AI",
        subheadline="Nous avons préparé un lien sécurisé pour reprendre le contrôle de votre compte.",
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
