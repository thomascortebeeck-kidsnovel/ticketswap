import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from web.app import app

    return TestClient(app)


# --- minimal smoke tests ---

def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_index_renders_form(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "TicketSwap helper" in r.text
    assert "WhatsApp" in r.text
    assert 'name="event_url"' in r.text


# --- happy path: WhatsApp only, returns a zip ---

VALID_FORM = {
    "whatsapp_phone": "+32 472 12 34 56",
    "whatsapp_apikey": "1234567",
    "event_url": "https://www.ticketswap.com/concert-tickets/rosalia-antwerp-afas-dome-2026-04-27-CVoAVJWtL6zMBsyXm3fYp",
    "event_label": "Rosalia Antwerp",
    "event_max_price": "200",
    "event_quantity": "1",
    "event_mode": "auto",
    "event_poll": "60",
}


def test_generate_returns_zip_for_valid_input(client):
    r = client.post("/generate", data=VALID_FORM)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert 'attachment; filename="ticketswap-config.zip"' in r.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = sorted(zf.namelist())
        assert names == [
            "ticketswap-config/.env",
            "ticketswap-config/INSTALL.txt",
            "ticketswap-config/watches.json",
        ]
        env = zf.read("ticketswap-config/.env").decode()
        watches = json.loads(zf.read("ticketswap-config/watches.json"))
        install = zf.read("ticketswap-config/INSTALL.txt").decode()

    # phone normalised
    assert "WHATSAPP_PHONE=32472123456" in env
    assert "WHATSAPP_APIKEY=1234567" in env
    # email not enabled -> no SMTP lines
    assert "SMTP_HOST=" not in env
    # watches.json is valid + matches what we asked for
    assert len(watches) == 1
    w = watches[0]
    assert w["label"] == "Rosalia Antwerp"
    assert w["max_price_eur"] == 200
    assert w["quantity"] == 1
    assert w["mode"] == "auto"
    assert w["polling_seconds"] == 60
    # install steps mention the key commands
    assert "python -m ticketswap login" in install
    assert "python -m ticketswap run" in install


def test_generate_with_email_enabled_includes_smtp(client):
    form = {
        **VALID_FORM,
        "email_enabled": "on",
        "smtp_user": "thomas@example.com",
        "smtp_pass": "xxxx yyyy zzzz wwww",
        "alert_to": "thomas@example.com",
        "imap_enabled": "on",
    }
    r = client.post("/generate", data=form)
    assert r.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        env = zf.read("ticketswap-config/.env").decode()
    assert "SMTP_HOST=smtp.gmail.com" in env
    assert "SMTP_USER=thomas@example.com" in env
    assert "SMTP_PASS=xxxx yyyy zzzz wwww" in env
    assert "ALERT_TO=thomas@example.com" in env
    assert "IMAP_HOST=imap.gmail.com" in env


# --- validation errors ---

def test_rejects_bad_phone(client):
    form = {**VALID_FORM, "whatsapp_phone": "abc"}
    r = client.post("/generate", data=form)
    assert r.status_code == 400
    assert "WhatsApp number" in r.text


def test_rejects_non_ticketswap_url(client):
    form = {**VALID_FORM, "event_url": "https://example.com/foo"}
    r = client.post("/generate", data=form)
    assert r.status_code == 400
    assert "ticketswap.com" in r.text.lower()


def test_rejects_too_aggressive_polling(client):
    form = {**VALID_FORM, "event_poll": "5"}
    r = client.post("/generate", data=form)
    assert r.status_code == 400
    assert "30 seconds" in r.text


def test_rejects_email_enabled_without_credentials(client):
    form = {**VALID_FORM, "email_enabled": "on"}
    r = client.post("/generate", data=form)
    assert r.status_code == 400
    assert "Email" in r.text or "SMTP" in r.text


# --- access password gate ---

def test_access_password_blocks_when_set(client, monkeypatch):
    monkeypatch.setattr("web.app.ACCESS_PASSWORD", "letmein")
    r = client.post("/generate", data=VALID_FORM)
    assert r.status_code == 401
    # with the right password, succeeds
    r = client.post("/generate", data={**VALID_FORM, "access_password": "letmein"})
    assert r.status_code == 200
