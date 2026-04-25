from __future__ import annotations

import random
import re
from threading import Event

import httpx

# Cheap availability heuristic on the public HTML. We do this before firing the
# heavyweight Playwright claimer so the bot doesn't open a browser every poll.
_AVAILABILITY_HINTS = re.compile(
    r"(/buy/|/checkout/|add to cart|reserve now|koop ticket)", re.IGNORECASE
)
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def looks_available(html: str) -> bool:
    return bool(_AVAILABILITY_HINTS.search(html))


def fetch_html(url: str, timeout: float = 10.0) -> tuple[int, str]:
    """GET the URL anonymously and return (status, html). Caller handles errors."""
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    r = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    return r.status_code, r.text


def sleep_with_jitter(seconds: int, stop: Event, jitter_pct: float = 0.25) -> bool:
    """Sleep for `seconds` ± jitter. Returns True if stopped early."""
    span = seconds * jitter_pct
    total = max(1.0, seconds + random.uniform(-span, span))
    return stop.wait(total)
