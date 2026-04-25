from __future__ import annotations

import json
from pathlib import Path

import click

from .claimer import claim_url
from .config import Watch, load_settings, load_watches
from .login import do_login
from .runner import run_watch_loop


@click.group(help="Local TicketSwap reservation sniper.")
def cli() -> None:
    pass


@cli.command()
def login() -> None:
    """One-time interactive TicketSwap login. Saves session locally."""
    do_login(load_settings())


@cli.command()
@click.argument("url")
@click.option("--max-price", type=float, default=None, help="Skip if cheapest > this.")
@click.option("--headed/--headless", default=False, help="Show the browser window.")
def test(url: str, max_price: float | None, headed: bool) -> None:
    """Run the claim flow once against URL (dry run, no email)."""
    settings = load_settings()
    result = claim_url(settings, url, max_price_eur=max_price, headless=not headed)
    click.echo(f"success: {result.success}")
    click.echo(f"message: {result.message}")
    click.echo(f"final_url: {result.final_url}")
    click.echo(f"screenshot: {result.screenshot}")


@cli.command()
def run() -> None:
    """Start the main watch loop (polling + optional IMAP listener)."""
    run_watch_loop(load_settings())


@cli.command(name="list")
def list_cmd() -> None:
    """List configured watches."""
    settings = load_settings()
    for w in load_watches(settings.watches_path):
        flag = "ON " if w.active else "off"
        click.echo(f"[{flag}] {w.label}  poll={w.polling_seconds}s  max=€{w.max_price_eur}")
        click.echo(f"       {w.url}")


@cli.command()
@click.argument("url")
@click.option("--label", required=True, help="Human-readable label (e.g. 'Rosalia Antwerp').")
@click.option("--max-price", type=float, required=False)
@click.option("--poll", "polling_seconds", type=int, default=60,
              help="Polling interval in seconds. 0 = IMAP-only.")
def add(url: str, label: str, max_price: float | None, polling_seconds: int) -> None:
    """Add a watch to watches.json."""
    settings = load_settings()
    path = settings.watches_path
    existing = load_watches(path) if path.exists() else []
    existing.append(
        Watch(
            label=label,
            url=url,
            max_price_eur=max_price,
            active=True,
            polling_seconds=polling_seconds,
        )
    )
    _write_watches(path, existing)
    click.echo(f"Added {label}. Total watches: {len(existing)}")


@cli.command()
@click.argument("label")
def remove(label: str) -> None:
    """Remove a watch by label (substring match)."""
    settings = load_settings()
    existing = load_watches(settings.watches_path)
    keep = [w for w in existing if label.lower() not in w.label.lower()]
    if len(keep) == len(existing):
        click.echo(f"No watch matched {label!r}")
        return
    _write_watches(settings.watches_path, keep)
    click.echo(f"Removed {len(existing) - len(keep)} watch(es).")


def _write_watches(path: Path, watches: list[Watch]) -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "label": w.label,
                    "url": w.url,
                    "max_price_eur": w.max_price_eur,
                    "active": w.active,
                    "polling_seconds": w.polling_seconds,
                    "cooldown_seconds": w.cooldown_seconds,
                }
                for w in watches
            ],
            indent=2,
        )
        + "\n"
    )
