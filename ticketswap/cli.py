from __future__ import annotations

import json
from pathlib import Path

import click

from .claimer import claim_url
from .config import WATCH_MODES, Watch, load_settings, load_watches
from .login import do_login
from .notifier import build_messages, send_alert
from .push import send_push
from .runner import run_watch_loop


@click.group(help="Local TicketSwap reservation sniper.")
def cli() -> None:
    pass


@cli.command()
def setup() -> None:
    """Interactive setup. Writes .env with SMTP/IMAP/alert email."""
    env_path = Path(".env")
    existing = _read_env(env_path)

    click.echo("Configuring TicketSwap. Press Enter to keep an existing value.\n")

    smtp_host = click.prompt("SMTP host", default=existing.get("SMTP_HOST", "smtp.gmail.com"))
    smtp_port = click.prompt(
        "SMTP port", default=int(existing.get("SMTP_PORT", "587")), type=int
    )
    smtp_user = click.prompt(
        "SMTP user (the email address that will SEND alerts)",
        default=existing.get("SMTP_USER", ""),
    )
    smtp_pass = click.prompt(
        "SMTP password (Gmail: an App Password)",
        default=existing.get("SMTP_PASS", ""),
        hide_input=True,
        show_default=False,
    )
    alert_to = click.prompt(
        "Alert recipient (the email address that will RECEIVE alerts)",
        default=existing.get("ALERT_TO", smtp_user),
    )

    use_imap = click.confirm(
        "Configure IMAP IDLE listener? (Faster than polling, optional)",
        default=bool(existing.get("IMAP_HOST")),
    )
    if use_imap:
        imap_host = click.prompt("IMAP host", default=existing.get("IMAP_HOST", "imap.gmail.com"))
        imap_user = click.prompt("IMAP user", default=existing.get("IMAP_USER", smtp_user))
        imap_pass = click.prompt(
            "IMAP password",
            default=existing.get("IMAP_PASS", smtp_pass),
            hide_input=True,
            show_default=False,
        )
    else:
        imap_host = imap_user = imap_pass = ""

    use_push = click.confirm(
        "Configure ntfy.sh push notifications? "
        "(Free, instant tap-to-open notification on your phone.)",
        default=bool(existing.get("NTFY_URL")),
    )
    if use_push:
        click.echo(
            "\nPick a long random topic name - it's the only auth on ntfy.sh.\n"
            "  Example: ticketswap-thomas-9f2k7p3qz4\n"
            "Install the 'ntfy' app on your phone and subscribe to the same\n"
            "topic so notifications arrive there.\n"
        )
        ntfy_url = click.prompt(
            "Full ntfy URL (https://ntfy.sh/<your-topic>)",
            default=existing.get("NTFY_URL", "https://ntfy.sh/"),
        )
    else:
        ntfy_url = ""

    profile_dir = existing.get("TICKETSWAP_PROFILE_DIR", "./.chromium-profile")
    watches_path = existing.get("WATCHES_PATH", "./watches.json")

    lines = [
        f"SMTP_HOST={smtp_host}",
        f"SMTP_PORT={smtp_port}",
        f"SMTP_USER={smtp_user}",
        f"SMTP_PASS={smtp_pass}",
        f"ALERT_TO={alert_to}",
        f"IMAP_HOST={imap_host}",
        f"IMAP_USER={imap_user}",
        f"IMAP_PASS={imap_pass}",
        f"NTFY_URL={ntfy_url}",
        f"TICKETSWAP_PROFILE_DIR={profile_dir}",
        f"WATCHES_PATH={watches_path}",
    ]
    env_path.write_text("\n".join(lines) + "\n")
    click.echo(f"\nWrote {env_path.resolve()}")
    click.echo("Next: run `python -m ticketswap login`.")


@cli.command()
def login() -> None:
    """One-time interactive TicketSwap login. Saves session locally."""
    do_login(load_settings())


@cli.command()
@click.argument("url")
@click.option("--max-price", type=float, default=None, help="Skip if cheapest > this.")
@click.option("--quantity", type=int, default=None, help="(Informational; see PLAN.md.)")
@click.option("--mode", type=click.Choice(WATCH_MODES), default="auto",
              help="fcfs = buy only; raffle = join raffle only; auto = try both.")
@click.option("--headed/--headless", default=False, help="Show the browser window.")
def test(
    url: str,
    max_price: float | None,
    quantity: int | None,
    mode: str,
    headed: bool,
) -> None:
    """Run the claim flow once against URL (dry run, no email)."""
    settings = load_settings()
    result = claim_url(
        settings,
        url,
        max_price_eur=max_price,
        mode=mode,
        quantity=quantity,
        headless=not headed,
    )
    click.echo(f"success: {result.success}")
    click.echo(f"kind:    {result.kind}")
    click.echo(f"message: {result.message}")
    click.echo(f"final_url: {result.final_url}")
    click.echo(f"screenshot: {result.screenshot}")


@cli.command()
def run() -> None:
    """Start the main watch loop (polling + optional IMAP listener)."""
    run_watch_loop(load_settings())


@cli.command(name="test-alerts")
def test_alerts() -> None:
    """Send a fake-success email + push so you can confirm both channels work."""
    settings = load_settings()
    subject, text, html = build_messages(
        label="Test Watch",
        cart_url="https://www.ticketswap.com/",
        listing_url="https://www.ticketswap.com/",
        kind="reservation",
        message="Test - no real reservation happened.",
    )
    subject = "[TEST] " + subject

    click.echo(f"Email -> {settings.alert_to}")
    try:
        send_alert(settings, subject, text, html)
        click.echo("  ok")
    except Exception as e:
        click.echo(f"  FAILED: {e}")

    if settings.ntfy_url:
        click.echo(f"Push  -> {settings.ntfy_url}")
        try:
            send_push(
                settings.ntfy_url,
                subject,
                "If you see this on your phone, push works.",
                "https://www.ticketswap.com/",
            )
            click.echo("  ok")
        except Exception as e:
            click.echo(f"  FAILED: {e}")
    else:
        click.echo("Push -> skipped (NTFY_URL is empty)")


@cli.command(name="list")
def list_cmd() -> None:
    """List configured watches."""
    settings = load_settings()
    for w in load_watches(settings.watches_path):
        flag = "ON " if w.active else "off"
        qty = f"qty={w.quantity}" if w.quantity is not None else "qty=any"
        click.echo(
            f"[{flag}] {w.label}  mode={w.mode}  poll={w.polling_seconds}s  "
            f"max=€{w.max_price_eur}  {qty}"
        )
        click.echo(f"       {w.url}")


@cli.command()
@click.argument("url")
@click.option("--label", required=True, help="Human-readable label (e.g. 'Rosalia Antwerp').")
@click.option("--max-price", type=float, default=None)
@click.option("--quantity", type=int, default=None,
              help="Number of tickets you want (currently informational).")
@click.option("--mode", type=click.Choice(WATCH_MODES), default="auto",
              help="fcfs = buy only; raffle = join raffle only; auto = try both.")
@click.option("--poll", "polling_seconds", type=int, default=60,
              help="Polling interval in seconds. 0 = IMAP-only.")
def add(
    url: str,
    label: str,
    max_price: float | None,
    quantity: int | None,
    mode: str,
    polling_seconds: int,
) -> None:
    """Add a watch to watches.json."""
    settings = load_settings()
    path = settings.watches_path
    existing = load_watches(path) if path.exists() else []
    existing.append(
        Watch(
            label=label,
            url=url,
            max_price_eur=max_price,
            quantity=quantity,
            mode=mode,
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
                    "quantity": w.quantity,
                    "mode": w.mode,
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


def _read_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out
