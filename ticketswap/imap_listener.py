from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass

from imap_tools import AND, MailBox

from .config import Settings
from .matcher import extract_ticketswap_urls


@dataclass
class TicketAlert:
    subject: str
    sender: str
    urls: list[str]


def stream_alerts(settings: Settings) -> Iterator[TicketAlert]:
    """Yield TicketSwap alert emails as they arrive (via IMAP IDLE).

    Reconnects on transport errors. Runs forever; caller breaks the loop.
    """
    if not (settings.imap_host and settings.imap_user and settings.imap_pass):
        return

    while True:
        try:
            with MailBox(settings.imap_host).login(
                settings.imap_user, settings.imap_pass, "INBOX"
            ) as mb:
                for msg in mb.fetch(
                    AND(seen=False, from_="ticketswap.com"),
                    mark_seen=True,
                    limit=20,
                    reverse=True,
                ):
                    urls = extract_ticketswap_urls(msg.html or msg.text or "")
                    if urls:
                        yield TicketAlert(msg.subject, msg.from_, urls)

                while True:
                    responses = mb.idle.wait(timeout=60)
                    if not responses:
                        continue
                    for msg in mb.fetch(
                        AND(seen=False, from_="ticketswap.com"),
                        mark_seen=True,
                        limit=20,
                        reverse=True,
                    ):
                        urls = extract_ticketswap_urls(msg.html or msg.text or "")
                        if urls:
                            yield TicketAlert(msg.subject, msg.from_, urls)
        except Exception as e:
            print(f"[imap] error: {e}; reconnecting in 30s")
            time.sleep(30)
