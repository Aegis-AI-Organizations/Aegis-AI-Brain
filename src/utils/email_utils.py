import logging
from html import escape
from urllib.parse import urlencode

from config.config import (
    FRONTEND_BASE_URL,
    ONBOARDING_EMAIL_ENABLED,
)
from services.email_service import EmailService, create_email_service

logger = logging.getLogger(__name__)

BRAND_NAME = "Aegis AI"
BRAND_TAGLINE = "Secure access workflows"
BRAND_LOGO_URL = "https://app.aegis-ai.fr/logo.png"
BRAND_LOGO_ALT = "Aegis AI Logo"
BRAND_PRIMARY = "#22d3ee"
BRAND_PRIMARY_DEEP = "#38bdf8"
BRAND_ACCENT = "#60a5fa"
SURFACE_DARK = "#0b0d13"
SURFACE_DARKER = "#050810"
TEXT_MAIN = "#e5eef9"
TEXT_MUTED = "#94a3b8"


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
    preheader = f"Un accès sécurisé Aegis AI est prêt pour {recipient_name} chez {company_name}."

    text_body = "\n".join(
        [
            f"Bonjour {recipient_name},",
            "",
            f"{BRAND_NAME} · {eyebrow}",
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
            company_name,
        ]
    )

    html_body = f"""
<html>
  <body style="margin:0;padding:0;background:{SURFACE_DARKER};">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;font-size:1px;line-height:1px;">
      {escape(preheader)}
    </div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{SURFACE_DARKER};padding:32px 16px;font-family:Inter,Arial,sans-serif;color:{TEXT_MAIN};">
      <tr>
        <td align="center">
          <table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:640px;background:{SURFACE_DARK};border:1px solid rgba(96,165,250,0.16);border-radius:28px;overflow:hidden;box-shadow:0 30px 80px rgba(2,6,23,0.45);">
            <tr>
              <td style="padding:28px 28px 22px 28px;background:linear-gradient(180deg,rgba(11,13,19,0.98) 0%,rgba(5,8,16,1) 100%);border-bottom:1px solid rgba(96,165,250,0.14);">
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:100%;">
                  <tr>
                    <td valign="middle" style="padding-right:14px;width:64px;">
                      <img src="{BRAND_LOGO_URL}" width="52" height="52" alt="{BRAND_LOGO_ALT}" style="display:block;border:0;outline:none;text-decoration:none;border-radius:14px;box-shadow:0 0 0 1px rgba(96,165,250,0.22),0 14px 26px rgba(34,211,238,0.12);" />
                    </td>
                    <td valign="middle">
                      <div style="font-size:12px;line-height:1.2;letter-spacing:0.22em;text-transform:uppercase;font-weight:800;color:{BRAND_PRIMARY};">{BRAND_NAME}</div>
                      <div style="margin-top:4px;font-size:13px;line-height:1.4;color:{TEXT_MUTED};">{BRAND_TAGLINE}</div>
                    </td>
                  </tr>
                </table>

                <div style="display:inline-block;margin-top:22px;padding:7px 12px;border-radius:999px;background:rgba(34,211,238,0.12);border:1px solid rgba(34,211,238,0.22);color:{BRAND_PRIMARY};font-size:11px;line-height:1;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;">
                  {safe_eyebrow}
                </div>

                <h1 style="margin:18px 0 12px 0;font-size:30px;line-height:1.15;font-weight:800;letter-spacing:-0.03em;color:{TEXT_MAIN};">
                  {safe_headline}
                </h1>

                <p style="margin:0 0 10px 0;font-size:18px;line-height:1.6;font-weight:700;color:#f8fbff;">
                  Bonjour {safe_recipient_name},
                </p>
                <p style="margin:0 0 12px 0;font-size:16px;line-height:1.7;color:{TEXT_MAIN};">
                  {safe_subheadline}
                </p>
                <p style="margin:0 0 12px 0;font-size:16px;line-height:1.7;color:{TEXT_MUTED};">
                  {safe_intro_sentence}
                </p>
                <p style="margin:0 0 22px 0;font-size:16px;line-height:1.7;color:{TEXT_MUTED};">
                  {safe_body_sentence}
                </p>

                <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 18px 0;">
                  <tr>
                    <td style="border-radius:999px;background:linear-gradient(135deg,{BRAND_PRIMARY} 0%,{BRAND_ACCENT} 100%);box-shadow:0 14px 30px rgba(34,211,238,0.16);">
                      <a href="{safe_action_url}" style="display:inline-block;padding:15px 24px;color:#08111f;text-decoration:none;font-size:15px;line-height:1;font-weight:800;border-radius:999px;">
                        {safe_action_label}
                      </a>
                    </td>
                  </tr>
                </table>

                <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:separate;">
                  <tr>
                    <td style="padding:16px 18px;border-radius:18px;background:rgba(148,163,184,0.08);border:1px solid rgba(148,163,184,0.16);">
                      <div style="font-size:11px;line-height:1.4;letter-spacing:0.12em;text-transform:uppercase;font-weight:800;color:{BRAND_PRIMARY};margin-bottom:6px;">
                        Sécurité
                      </div>
                      <div style="font-size:14px;line-height:1.7;color:{TEXT_MAIN};">
                        {safe_security_note}
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:20px 28px 24px 28px;background:#070a11;border-top:1px solid rgba(96,165,250,0.12);">
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:100%;">
                  <tr>
                    <td style="font-size:13px;line-height:1.6;color:{TEXT_MUTED};font-weight:700;">
                      {safe_closing_line}
                    </td>
                  </tr>
                  <tr>
                    <td style="padding-top:6px;font-size:13px;line-height:1.6;color:{TEXT_MUTED};">
                      {safe_company_name}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
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
