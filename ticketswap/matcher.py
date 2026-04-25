from __future__ import annotations

import re
from urllib.parse import urlparse

from .config import Watch

# TicketSwap URLs end in a 21-character base62-ish event id, e.g.
# /concert-tickets/rosalia-antwerp-afas-dome-2026-04-27-CVoAVJWtL6zMBsyXm3fYp
_EVENT_ID_RE = re.compile(r"-([A-Za-z0-9]{16,32})$")
_TS_URL_RE = re.compile(r"https?://(?:www\.)?ticketswap\.com/[^\s\"'<>]+")


def event_id(url: str) -> str | None:
    """Extract TicketSwap's trailing event id from a URL.

    Returns None if no plausible id is found.
    """
    if not url:
        return None
    path = urlparse(url).path.rstrip("/")
    last = path.rsplit("/", 1)[-1]
    m = _EVENT_ID_RE.search(last)
    return m.group(1) if m else None


def extract_ticketswap_urls(text: str) -> list[str]:
    """Find all TicketSwap URLs in a string (HTML or plain text)."""
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for u in _TS_URL_RE.findall(text):
        u = u.rstrip(".,)\"'")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def match_alert_to_watches(
    alert_urls: list[str], watches: list[Watch]
) -> list[tuple[Watch, str]]:
    """Pair each watch with the first alert URL whose event id matches it."""
    out: list[tuple[Watch, str]] = []
    for w in watches:
        if not w.active:
            continue
        wid = event_id(w.url)
        if not wid:
            continue
        for u in alert_urls:
            if event_id(u) == wid:
                out.append((w, u))
                break
    return out
