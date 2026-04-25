from ticketswap.config import Watch
from ticketswap.matcher import (
    event_id,
    extract_ticketswap_urls,
    match_alert_to_watches,
)


ROSALIA_URL = (
    "https://www.ticketswap.com/concert-tickets/"
    "rosalia-antwerp-afas-dome-2026-04-27-CVoAVJWtL6zMBsyXm3fYp"
)


def test_event_id_extracts_trailing_id():
    assert event_id(ROSALIA_URL) == "CVoAVJWtL6zMBsyXm3fYp"


def test_event_id_strips_query_string():
    url = ROSALIA_URL + "?utm_source=internal&utm_medium=share"
    assert event_id(url) == "CVoAVJWtL6zMBsyXm3fYp"


def test_event_id_returns_none_on_garbage():
    assert event_id("https://example.com/whatever") is None
    assert event_id("") is None


def test_extract_urls_from_html_blob():
    html = f"""
    <html><body>
      <p>New ticket! Click <a href="{ROSALIA_URL}?x=1">here</a> to buy.</p>
      <p>Also see https://www.ticketswap.com/event/foo-bar-AbCdEfGhIjKlMnOpQrStU.</p>
    </body></html>
    """
    urls = extract_ticketswap_urls(html)
    assert len(urls) == 2
    assert any("CVoAVJWtL6zMBsyXm3fYp" in u for u in urls)
    assert any("AbCdEfGhIjKlMnOpQrStU" in u for u in urls)


def test_match_alert_to_watches_matches_by_event_id():
    watches = [
        Watch(label="rosalia", url=ROSALIA_URL),
        Watch(label="other", url="https://www.ticketswap.com/event/foo-AbCdEfGhIjKlMnOpQrStU"),
    ]
    alert_urls = [ROSALIA_URL + "?utm=email"]
    matches = match_alert_to_watches(alert_urls, watches)
    assert len(matches) == 1
    assert matches[0][0].label == "rosalia"


def test_match_alert_skips_inactive_watches():
    watches = [Watch(label="rosalia", url=ROSALIA_URL, active=False)]
    matches = match_alert_to_watches([ROSALIA_URL], watches)
    assert matches == []
