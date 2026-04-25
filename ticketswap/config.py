from __future__ import annotations

import dataclasses
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# What the claimer will try to do when a listing appears.
# - "fcfs":   only click the buy/reserve button
# - "raffle": only click the join-raffle / waiting-list button
# - "auto":   try buy first, fall back to raffle (works for either sale type)
WATCH_MODES = ("fcfs", "raffle", "auto")


@dataclass
class Watch:
    label: str
    url: str
    max_price_eur: float | None = None
    quantity: int | None = None
    mode: str = "auto"
    active: bool = True
    polling_seconds: int = 0
    cooldown_seconds: int = 600

    def __post_init__(self) -> None:
        if self.mode not in WATCH_MODES:
            raise ValueError(f"mode must be one of {WATCH_MODES}, got {self.mode!r}")


@dataclass
class Settings:
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_pass: str | None
    alert_to: str | None
    imap_host: str | None
    imap_user: str | None
    imap_pass: str | None
    whatsapp_phone: str | None
    whatsapp_apikey: str | None
    profile_dir: Path
    watches_path: Path
    shots_dir: Path = field(default_factory=lambda: Path("./shots"))

    @property
    def email_enabled(self) -> bool:
        return all([self.smtp_host, self.smtp_user, self.smtp_pass, self.alert_to])

    @property
    def whatsapp_enabled(self) -> bool:
        return bool(self.whatsapp_phone and self.whatsapp_apikey)


def load_settings() -> Settings:
    return Settings(
        smtp_host=os.environ.get("SMTP_HOST") or None,
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        smtp_user=os.environ.get("SMTP_USER") or None,
        smtp_pass=os.environ.get("SMTP_PASS") or None,
        alert_to=os.environ.get("ALERT_TO") or None,
        imap_host=os.environ.get("IMAP_HOST") or None,
        imap_user=os.environ.get("IMAP_USER") or None,
        imap_pass=os.environ.get("IMAP_PASS") or None,
        whatsapp_phone=os.environ.get("WHATSAPP_PHONE") or None,
        whatsapp_apikey=os.environ.get("WHATSAPP_APIKEY") or None,
        profile_dir=Path(os.environ.get("TICKETSWAP_PROFILE_DIR", "./.chromium-profile")),
        watches_path=Path(os.environ.get("WATCHES_PATH", "./watches.json")),
    )


def load_watches(path: Path) -> list[Watch]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    fields = {f.name for f in dataclasses.fields(Watch)}
    return [Watch(**{k: v for k, v in item.items() if k in fields}) for item in raw]
