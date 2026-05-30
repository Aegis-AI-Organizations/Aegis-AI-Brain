from __future__ import annotations

import json
import logging
import os
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.message import EmailMessage
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config.config import (
    AEGIS_EMAIL_API_KEY,
    AEGIS_EMAIL_API_URL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USERNAME,
)

logger = logging.getLogger(__name__)

DEFAULT_FROM_NAME = "Aegis AI Team"
DEFAULT_FROM_EMAIL = "team@aegis-ai.fr"
DEFAULT_TIMEOUT_SECONDS = 10


class EmailService(ABC):
    @abstractmethod
    def send_email(self, to: str, subject: str, html_body: str, text_body: str) -> bool:
        raise NotImplementedError


def _format_from_header(name: str, email: str) -> str:
    return f"{name} <{email}>"


@dataclass(slots=True)
class MailpitEmailService(EmailService):
    host: str = "localhost"
    port: int = 1025
    from_name: str = DEFAULT_FROM_NAME
    from_email: str = DEFAULT_FROM_EMAIL
    username: str = ""
    password: str = ""
    use_tls: bool = False
    timeout: int = DEFAULT_TIMEOUT_SECONDS

    def send_email(self, to: str, subject: str, html_body: str, text_body: str) -> bool:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = _format_from_header(self.from_name, self.from_email)
        message["To"] = to
        message.set_content(text_body)
        if html_body:
            message.add_alternative(html_body, subtype="html")

        if self.use_tls:
            smtp = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout)
        else:
            smtp = smtplib.SMTP(self.host, self.port, timeout=self.timeout)

        with smtp:
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(message)

        logger.info("Mailpit email sent to %s", to)
        return True


@dataclass(slots=True)
class ProductionEmailService(EmailService):
    api_key: str
    api_url: str = AEGIS_EMAIL_API_URL
    from_name: str = DEFAULT_FROM_NAME
    from_email: str = DEFAULT_FROM_EMAIL
    timeout: int = DEFAULT_TIMEOUT_SECONDS

    def send_email(self, to: str, subject: str, html_body: str, text_body: str) -> bool:
        if not self.api_key:
            raise RuntimeError("AEGIS_EMAIL_API_KEY must be configured in production")

        payload = {
            "from": _format_from_header(self.from_name, self.from_email),
            "to": [to],
            "subject": subject,
            "html": html_body,
            "text": text_body,
        }
        request = Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Aegis-AI-Brain/1.0",
            },
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                status = getattr(response, "status", response.getcode())
                if status >= 400:
                    raise RuntimeError(f"Email provider returned HTTP {status}")
        except HTTPError as err:
            error_body = ""
            try:
                raw_body = err.read()
                if raw_body:
                    error_body = raw_body.decode("utf-8", errors="replace").strip()
            except Exception:
                error_body = ""

            if error_body:
                raise RuntimeError(
                    f"Email provider returned HTTP {err.code}: {error_body}"
                ) from err

            raise RuntimeError(f"Email provider returned HTTP {err.code}") from err
        except URLError as err:
            raise RuntimeError("Email provider request failed") from err

        logger.info("Production email sent to %s", to)
        return True


def create_email_service(env: str | None = None) -> EmailService:
    normalized_env = (env or os.getenv("ENV", "")).lower()
    if normalized_env == "production":
        if not AEGIS_EMAIL_API_KEY:
            raise RuntimeError("AEGIS_EMAIL_API_KEY must be configured in production")
        return ProductionEmailService(api_key=AEGIS_EMAIL_API_KEY)

    return MailpitEmailService(
        host=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USERNAME,
        password=SMTP_PASSWORD,
        use_tls=SMTP_USE_TLS,
    )
