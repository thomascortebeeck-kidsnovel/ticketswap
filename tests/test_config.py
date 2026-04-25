import json

import pytest

from ticketswap.config import Watch, load_watches


def test_watch_defaults():
    w = Watch(label="x", url="https://example.com")
    assert w.mode == "auto"
    assert w.quantity is None
    assert w.max_price_eur is None
    assert w.active is True


def test_watch_rejects_bad_mode():
    with pytest.raises(ValueError):
        Watch(label="x", url="https://example.com", mode="nope")


def test_load_watches_tolerates_unknown_fields(tmp_path):
    """Older or hand-edited JSON shouldn't crash the loader."""
    p = tmp_path / "watches.json"
    p.write_text(json.dumps([
        {
            "label": "old",
            "url": "https://example.com",
            "max_price_eur": 50,
            "polling_seconds": 30,
            "some_legacy_field": "ignored",
        }
    ]))
    out = load_watches(p)
    assert len(out) == 1
    assert out[0].label == "old"
    assert out[0].mode == "auto"  # default kicked in


def test_load_watches_round_trip(tmp_path):
    p = tmp_path / "watches.json"
    p.write_text(json.dumps([
        {
            "label": "rosalia",
            "url": "https://www.ticketswap.com/event/x-AbCdEfGhIjKlMnOpQrStU",
            "max_price_eur": 200,
            "quantity": 2,
            "mode": "fcfs",
            "active": True,
            "polling_seconds": 60,
            "cooldown_seconds": 600,
        }
    ]))
    out = load_watches(p)
    assert out[0].mode == "fcfs"
    assert out[0].quantity == 2
    assert out[0].max_price_eur == 200
