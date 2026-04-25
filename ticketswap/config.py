from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Watch:
    label: str
    url: str
    max_price_eur: float | None = None
    active: bool = True
    polling_seconds: int = 0
    cooldown_seconds: int = 600


@dataclass
class Settings:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str
    alert_to: str
    imap_host: str | None
    imap_user: str | None
    imap_pass: str | None
    profile_dir: Path
    watches_path: Path
    shots_dir: Path = field(default_factory=lambda: Path("./shots"))


def _required(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing required env var: {name}. See .env.example.")
    return val


def load_settings() -> Settings:
    return Settings(
        smtp_host=_required("SMTP_HOST"),
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        smtp_user=_required("SMTP_USER"),
        smtp_pass=_required("SMTP_PASS"),
        alert_to=_required("ALERT_TO"),
        imap_host=os.environ.get("IMAP_HOST") or None,
        imap_user=os.environ.get("IMAP_USER") or None,
        imap_pass=os.environ.get("IMAP_PASS") or None,
        profile_dir=Path(os.environ.get("TICKETSWAP_PROFILE_DIR", "./.chromium-profile")),
        watches_path=Path(os.environ.get("WATCHES_PATH", "./watches.json")),
    )


def load_watches(path: Path) -> list[Watch]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    return [Watch(**item) for item in raw]
