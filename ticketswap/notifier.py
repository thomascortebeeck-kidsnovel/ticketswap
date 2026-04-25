from __future__ import annotations

import html
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from .config import Settings


def build_messages(
    label: str,
    cart_url: str,
    listing_url: str,
    kind: str,
    message: str,
) -> tuple[str, str, str]:
    """Build (subject, plain_text, html) for a successful claim.

    Subject and plain-text are mobile-optimised: the cart URL is on the first
    body line so any email client makes it tappable. The HTML alternative
    renders a big tap target on phones.
    """
    if kind == "raffle":
        subject = f"[RAFFLE ENTERED] {label}"
        action_text = "You're in the raffle. Watch TicketSwap for the result."
        button_label = "Open raffle status"
    else:
        subject = f"[RESERVED] {label} - PAY NOW"
        action_text = "Reserved! Pay within ~10 minutes."
        button_label = "Open cart in TicketSwap"

    plain = "\n".join(
        [
            action_text,
            "",
            f"Open: {cart_url}",
            "",
            f"Listing: {listing_url}",
            f"Watch: {label}",
            f"Status: {message}",
        ]
    )

    html_body = _html_body(action_text, cart_url, button_label, listing_url, label, message)
    return subject, plain, html_body


def _html_body(
    action_text: str,
    cart_url: str,
    button_label: str,
    listing_url: str,
    label: str,
    message: str,
) -> str:
    cart = html.escape(cart_url, quote=True)
    listing = html.escape(listing_url, quote=True)
    return f"""<!doctype html>
<html><body style="margin:0;padding:24px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f6f7f9;color:#111;">
  <div style="max-width:520px;margin:0 auto;background:#fff;padding:24px;border-radius:12px;">
    <h1 style="margin:0 0 8px;font-size:22px;">{html.escape(action_text)}</h1>
    <p style="margin:0 0 24px;color:#555;font-size:14px;">{html.escape(label)}</p>
    <p style="margin:0 0 24px;">
      <a href="{cart}"
         style="display:block;text-align:center;padding:18px 24px;background:#0d6efd;color:#fff;
                text-decoration:none;border-radius:10px;font-size:18px;font-weight:600;">
        {html.escape(button_label)}
      </a>
    </p>
    <p style="margin:0 0 8px;font-size:13px;color:#555;">
      Tap the button above on your phone to open the cart in the TicketSwap app.
    </p>
    <hr style="border:0;border-top:1px solid #eee;margin:24px 0;">
    <p style="margin:0 0 4px;font-size:12px;color:#888;">Status: {html.escape(message)}</p>
    <p style="margin:0;font-size:12px;color:#888;">
      Listing: <a href="{listing}" style="color:#0d6efd;">{listing}</a>
    </p>
  </div>
</body></html>
"""


def send_alert(
    settings: Settings,
    subject: str,
    text_body: str,
    html_body: str | None = None,
    attachment: Path | None = None,
) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_user
    msg["To"] = settings.alert_to
    msg["Subject"] = subject
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

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
