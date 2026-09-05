"""Message delivery for background jobs.

Three interchangeable backends, chosen by NOTIFICATION_BACKEND:

* ``log``  (default) — renders the full message to var/notifications.log and the
  application logger. No credentials needed, and the output is complete enough
  to verify exactly what *would* have been sent.
* ``smtp`` — real email over stdlib smtplib.
* ``chat`` — posts to a Google Chat incoming webhook over stdlib urllib.

Everything above the backend boundary is identical in all three modes, so the
demo path exercises the same code that production would.
"""

import json
import logging
import smtplib
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from html import unescape
from re import sub as re_sub

from backend.config import Config

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    """Raised when a real send fails. Never raised by the log backend."""


def _html_to_text(html: str) -> str:
    """Rough plain-text fallback for email clients that refuse HTML."""
    text = re_sub(r"<br\s*/?>", "\n", html)
    text = re_sub(r"</(p|div|h[1-6]|li|tr)>", "\n", text)
    text = re_sub(r"<[^>]+>", "", text)
    return unescape(re_sub(r"\n{3,}", "\n\n", text)).strip()


def _write_log(record: dict) -> None:
    """Append one rendered message to the notification log file."""
    path = Config.NOTIFICATION_LOG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, default=str) + "\n")


def _send_via_log(to: str, subject: str, html_body: str, category: str) -> dict:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "backend": "log",
        "category": category,
        "to": to,
        "subject": subject,
        "body_text": _html_to_text(html_body),
        "body_html": html_body,
    }
    _write_log(record)
    logger.info("[notification:%s] to=%s subject=%s", category, to, subject)
    return {"delivered": True, "backend": "log", "to": to}


def _send_via_smtp(to: str, subject: str, html_body: str, category: str) -> dict:
    if not Config.SMTP_HOST:
        raise NotificationError("NOTIFICATION_BACKEND=smtp but SMTP_HOST is not set.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = Config.MAIL_FROM
    message["To"] = to
    message.set_content(_html_to_text(html_body))
    message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=30) as server:
            if Config.SMTP_USE_TLS:
                server.starttls()
            if Config.SMTP_USERNAME:
                server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as error:
        raise NotificationError(f"SMTP delivery failed: {error}") from error

    logger.info("[notification:%s] emailed %s", category, to)
    return {"delivered": True, "backend": "smtp", "to": to}


def _send_via_chat(to: str, subject: str, html_body: str, category: str) -> dict:
    if not Config.GOOGLE_CHAT_WEBHOOK_URL:
        raise NotificationError(
            "NOTIFICATION_BACKEND=chat but GOOGLE_CHAT_WEBHOOK_URL is not set."
        )

    payload = json.dumps(
        {"text": f"*{subject}*\n_for {to}_\n\n{_html_to_text(html_body)}"}
    ).encode("utf-8")
    request = urllib.request.Request(
        Config.GOOGLE_CHAT_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json; charset=UTF-8"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
    except (urllib.error.URLError, OSError) as error:
        raise NotificationError(f"Google Chat delivery failed: {error}") from error

    logger.info("[notification:%s] posted to Google Chat for %s", category, to)
    return {"delivered": True, "backend": "chat", "to": to}


_BACKENDS = {"log": _send_via_log, "smtp": _send_via_smtp, "chat": _send_via_chat}


def send_notification(to: str, subject: str, html_body: str, category: str = "general") -> dict:
    """Deliver one message using the configured backend.

    Failures are caught and reported in the return value rather than raised, so
    one bad address can never abort a batch job mid-way.
    """
    backend_name = Config.NOTIFICATION_BACKEND
    backend = _BACKENDS.get(backend_name)
    if backend is None:
        logger.error("Unknown NOTIFICATION_BACKEND %r — falling back to log", backend_name)
        backend = _send_via_log

    try:
        return backend(to, subject, html_body, category)
    except NotificationError as error:
        logger.error("Notification to %s failed: %s", to, error)
        return {"delivered": False, "backend": backend_name, "to": to, "error": str(error)}
