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
BRAND_PRIMARY = "#00f2ff"  # Neon Cyan
BRAND_PRIMARY_DEEP = "#00d9e6"  # Accent Cyan
BRAND_ACCENT = "#7000ff"  # Neon Purple
SURFACE_DARK = "#0B0D13"  # Card background
SURFACE_DARKER = "#050810"  # Shell background
TEXT_MAIN = "#e5e7eb"  # Main text
TEXT_MUTED = "#9ca3af"  # Muted text


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
<html bgcolor="{SURFACE_DARKER}">
  <head>
    <meta name="color-scheme" content="light dark" />
    <meta name="supported-color-schemes" content="light dark" />
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@800;900&family=Inter:wght@400;500;700;800&display=swap" rel="stylesheet" />
    <style>
      body.email-body {{ margin: 0 !important; padding: 0 !important; background: {SURFACE_DARKER} !important; background-color: {SURFACE_DARKER} !important; }}
      table.email-shell, td.email-shell {{ background: {SURFACE_DARKER} !important; background-color: {SURFACE_DARKER} !important; }}
      table.email-card, td.email-card {{ background: {SURFACE_DARK} !important; background-color: {SURFACE_DARK} !important; }}
      table.email-footer, td.email-footer {{ background: #050810 !important; background-color: #050810 !important; }}
      .email-text-main {{ color: {TEXT_MAIN} !important; }}
      .email-text-muted {{ color: {TEXT_MUTED} !important; }}
      [data-ogsc] body.email-body {{ background: {SURFACE_DARKER} !important; background-color: {SURFACE_DARKER} !important; }}
      [data-ogsc] table.email-shell, [data-ogsc] td.email-shell {{ background: {SURFACE_DARKER} !important; background-color: {SURFACE_DARKER} !important; }}
      [data-ogsc] table.email-card, [data-ogsc] td.email-card {{ background: {SURFACE_DARK} !important; background-color: {SURFACE_DARK} !important; }}
      [data-ogsc] table.email-footer, [data-ogsc] td.email-footer {{ background: #050810 !important; background-color: #050810 !important; }}
      [data-ogsc] .email-text-main {{ color: {TEXT_MAIN} !important; }}
      [data-ogsc] .email-text-muted {{ color: {TEXT_MUTED} !important; }}
    </style>
  </head>
  <body class="email-body" bgcolor="{SURFACE_DARKER}" style="margin:0;padding:0;background:{SURFACE_DARKER};background-color:{SURFACE_DARKER};">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;font-size:1px;line-height:1px;">
      {escape(preheader)}
    </div>
    <table
      class="email-shell"
      role="presentation"
      width="100%"
      cellpadding="0"
      cellspacing="0"
      border="0"
      bgcolor="{SURFACE_DARKER}"
      style="background:{SURFACE_DARKER};background-color:{SURFACE_DARKER};padding:40px 16px;font-family:'Inter', Arial, sans-serif;color:{TEXT_MAIN};mso-table-lspace:0pt;mso-table-rspace:0pt;"
    >
      <tr>
        <td class="email-shell" align="center" bgcolor="{SURFACE_DARKER}" style="background:{SURFACE_DARKER};background-color:{SURFACE_DARKER};">
          <table
            class="email-card"
            role="presentation"
            width="600"
            cellpadding="0"
            cellspacing="0"
            border="0"
            bgcolor="{SURFACE_DARK}"
            style="width:100%;max-width:600px;background:{SURFACE_DARK};background-color:{SURFACE_DARK};border:1px solid #1e293b;border-radius:24px;overflow:hidden;mso-table-lspace:0pt;mso-table-rspace:0pt;"
          >
            <tr>
              <td class="email-card" bgcolor="{SURFACE_DARK}" style="padding:0;background:{SURFACE_DARK};background-color:{SURFACE_DARK};">
                <div style="height:4px;background-color:{BRAND_PRIMARY};line-height:4px;font-size:4px;">&nbsp;</div>
              </td>
            </tr>
            <tr>
              <td class="email-card" bgcolor="{SURFACE_DARK}" style="padding:32px 32px 24px 32px;background:{SURFACE_DARK};background-color:{SURFACE_DARK};">
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:100%;">
                  <tr>
                    <td valign="middle" style="padding-right:16px;width:66px;">
                      <img src="{BRAND_LOGO_URL}" width="54" height="54" alt="{BRAND_LOGO_ALT}" style="display:block;border:0;outline:none;text-decoration:none;border-radius:12px;background-color:#0f172a;border:1px solid #1e293b;" />
                    </td>
                    <td valign="middle">
                      <div class="email-text-main" style="font-family:'Orbitron', 'Inter', sans-serif;font-size:14px;line-height:1.2;letter-spacing:0.2em;text-transform:uppercase;font-weight:900;color:{BRAND_PRIMARY};">{BRAND_NAME}</div>
                      <div class="email-text-muted" style="margin-top:4px;font-size:12px;line-height:1.4;color:{TEXT_MUTED};">{BRAND_TAGLINE}</div>
                    </td>
                    <td valign="middle" align="right" style="font-family:'Orbitron', 'Inter', sans-serif;font-size:10px;line-height:1.2;letter-spacing:0.15em;text-transform:uppercase;color:{BRAND_PRIMARY};font-weight:700;">
                      {safe_eyebrow}
                    </td>
                  </tr>
                </table>

                <div style="height:1px;background:#1e293b;margin:24px 0 24px 0;"></div>

                <div style="font-family:'Orbitron', 'Inter', sans-serif;font-size:11px;line-height:1.4;letter-spacing:0.15em;text-transform:uppercase;font-weight:900;color:{BRAND_PRIMARY};margin-bottom:8px;">
                  Cybersecurity Platform
                </div>
                <h1 class="email-text-main" style="margin:0;font-family:'Orbitron', 'Inter', sans-serif;font-size:28px;line-height:1.2;font-weight:900;letter-spacing:-0.02em;color:#ffffff;">
                  {safe_headline}
                </h1>

                <p class="email-text-main" style="margin:24px 0 12px 0;font-size:16px;line-height:1.6;font-weight:700;color:#ffffff;">
                  Bonjour {safe_recipient_name},
                </p>
                <p class="email-text-main" style="margin:0 0 12px 0;font-size:15px;line-height:1.6;color:{TEXT_MAIN};">
                  {safe_subheadline}
                </p>
                <p class="email-text-muted" style="margin:0 0 12px 0;font-size:15px;line-height:1.6;color:{TEXT_MUTED};">
                  {safe_intro_sentence}
                </p>
                <p class="email-text-muted" style="margin:0 0 24px 0;font-size:15px;line-height:1.6;color:{TEXT_MUTED};">
                  {safe_body_sentence}
                </p>

                <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0 24px 0;width:100%;">
                  <tr>
                    <td align="left">
                      <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                        <tr>
                          <td style="border-radius:12px;background-color:{BRAND_PRIMARY};">
                            <a href="{safe_action_url}" style="display:inline-block;padding:14px 28px;color:#050810;text-decoration:none;font-family:'Orbitron', 'Inter', sans-serif;font-size:14px;line-height:1;font-weight:900;text-transform:uppercase;letter-spacing:0.1em;border-radius:12px;background-color:{BRAND_PRIMARY};">
                              {safe_action_label}
                            </a>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>

                <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:100%;margin-top:24px;">
                  <tr>
                    <td style="padding:16px;border-radius:12px;background-color:#0f172a;border:1px solid #1e293b;border-left:4px solid {BRAND_PRIMARY};">
                      <div class="email-text-main" style="font-family:'Orbitron', 'Inter', sans-serif;font-size:11px;line-height:1.4;letter-spacing:0.15em;text-transform:uppercase;font-weight:900;color:{BRAND_PRIMARY};margin-bottom:6px;">
                        Sécurité
                      </div>
                      <div class="email-text-muted" style="font-size:13px;line-height:1.6;color:{TEXT_MUTED};">
                        {safe_security_note}
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td class="email-footer" bgcolor="#050810" style="padding:20px 32px 24px 32px;background:#050810;background-color:#050810;border-top:1px solid #1e293b;">
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:100%;">
                  <tr>
                    <td class="email-text-muted" style="font-size:13px;line-height:1.6;color:{TEXT_MUTED};font-weight:700;">
                      {safe_closing_line}
                    </td>
                    <td class="email-text-muted" align="right" style="font-size:13px;line-height:1.6;color:{TEXT_MUTED};text-align:right;">
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
