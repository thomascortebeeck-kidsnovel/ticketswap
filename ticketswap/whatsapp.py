from __future__ import annotations

import re

import httpx

# CallMeBot's free WhatsApp gateway. Each user has to register their phone
# number once with the bot and gets back a personal API key:
#   https://www.callmebot.com/blog/free-api-whatsapp-messages/
# The bot then accepts GET requests with phone + text + apikey.
_ENDPOINT = "https://api.callmebot.com/whatsapp.php"


def normalize_phone(raw: str) -> str:
    """Strip '+', spaces, dashes - CallMeBot wants digits only."""
    return re.sub(r"\D+", "", raw or "")


def send_whatsapp(phone: str, apikey: str, message: str) -> None:
    """Send a WhatsApp message via CallMeBot.

    `phone` must be the recipient's number in international format. '+',
    spaces, and dashes are stripped automatically.

    `apikey` is the personal key CallMeBot returned after you registered the
    number with their bot.
    """
    params = {
        "phone": normalize_phone(phone),
        "text": message,
        "apikey": apikey,
    }
    r = httpx.get(_ENDPOINT, params=params, timeout=15)
    r.raise_for_status()
    # CallMeBot returns 200 even on failures - inspect the body.
    body = r.text.lower()
    if "queued" not in body and "sent" not in body and "successfully" not in body:
        raise RuntimeError(f"CallMeBot rejected the request: {r.text.strip()[:200]}")
