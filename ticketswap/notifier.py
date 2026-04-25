from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from .config import Settings


def send_alert(
    settings: Settings,
    subject: str,
    body: str,
    attachment: Path | None = None,
) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_user
    msg["To"] = settings.alert_to
    msg["Subject"] = subject
    msg.set_content(body)

    if attachment is not None and attachment.exists():
        msg.add_attachment(
            attachment.read_bytes(),
            maintype="image",
            subtype="png",
            filename=attachment.name,
        )

    ctx = ssl.create_default_context()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls(context=ctx)
        server.login(settings.smtp_user, settings.smtp_pass)
        server.send_message(msg)
