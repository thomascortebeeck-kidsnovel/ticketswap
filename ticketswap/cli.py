from __future__ import annotations

import json
from pathlib import Path

import click

from .claimer import claim_url
from .config import WATCH_MODES, Watch, load_settings, load_watches
from .login import do_login
from .notifier import build_messages, send_alert
from .runner import run_watch_loop
from .whatsapp import normalize_phone, send_whatsapp


@click.group(help="Local TicketSwap reservation sniper.")
def cli() -> None:
    pass


@cli.command()
def setup() -> None:
    """Interactive setup. Writes .env with notification + IMAP settings."""
    env_path = Path(".env")
    existing = _read_env(env_path)

    click.echo("Configuring TicketSwap. Press Enter to keep an existing value.\n")

    # --- WhatsApp (recommended primary channel) ---
    click.echo("---- WhatsApp notifications (free, via CallMeBot) ----")
    use_whatsapp = click.confirm(
        "Configure WhatsApp notifications?",
        default=bool(existing.get("WHATSAPP_APIKEY")) or True,
    )
    if use_whatsapp:
        click.echo(
            "\nOne-time CallMeBot setup on your phone (do these steps now):\n"
            "  1. Save the CallMeBot bot number to your contacts. The number\n"
            "     and exact instructions are at:\n"
            "       https://www.callmebot.com/blog/free-api-whatsapp-messages/\n"
            "  2. Send this WhatsApp message to that contact:\n"
            "       I allow callmebot to send me messages\n"
            "  3. Wait for the reply. It contains your APIKEY.\n"
        )
        whatsapp_phone = click.prompt(
            "Your WhatsApp number in international format "
            "(e.g. +32472123456 or 32472123456)",
            default=existing.get("WHATSAPP_PHONE", ""),
        )
        whatsapp_phone = normalize_phone(whatsapp_phone)
        whatsapp_apikey = click.prompt(
            "Your CallMeBot APIKEY (the number you got back on WhatsApp)",
            default=existing.get("WHATSAPP_APIKEY", ""),
        )
    else:
        whatsapp_phone = ""
        whatsapp_apikey = ""

    # --- Email (now optional) ---
    click.echo("\n---- Email backup (optional) ----")
    click.echo(
        "Email is a backup channel. Skip it if WhatsApp is enough.\n"
        "Gmail needs an App Password, not your normal password:\n"
        "  https://myaccount.google.com/apppasswords\n"
    )
    use_email = click.confirm(
        "Configure email alerts?",
        default=bool(existing.get("SMTP_HOST")),
    )
    if use_email:
        smtp_host = click.prompt(
            "SMTP host", default=existing.get("SMTP_HOST", "smtp.gmail.com")
        )
        smtp_port = click.prompt(
            "SMTP port", default=int(existing.get("SMTP_PORT", "587")), type=int
        )
        smtp_user = click.prompt(
            "SMTP user (the email that SENDS alerts)",
            default=existing.get("SMTP_USER", ""),
        )
        smtp_pass = click.prompt(
            "SMTP password (Gmail App Password)",
            default=existing.get("SMTP_PASS", ""),
            hide_input=True,
            show_default=False,
        )
        alert_to = click.prompt(
            "Alert recipient (the email that RECEIVES alerts)",
            default=existing.get("ALERT_TO", smtp_user),
        )

        use_imap = click.confirm(
            "Also use this Gmail to listen for TicketSwap's official alert "
            "emails via IMAP? (Faster reactions; recommended.)",
            default=bool(existing.get("IMAP_HOST")) or True,
        )
        if use_imap:
            imap_host = click.prompt(
                "IMAP host", default=existing.get("IMAP_HOST", "imap.gmail.com")
            )
            imap_user = click.prompt(
                "IMAP user", default=existing.get("IMAP_USER", smtp_user)
            )
            imap_pass = click.prompt(
                "IMAP password",
                default=existing.get("IMAP_PASS", smtp_pass),
                hide_input=True,
                show_default=False,
            )
        else:
            imap_host = imap_user = imap_pass = ""
    else:
        smtp_host = smtp_port = smtp_user = smtp_pass = alert_to = ""
        smtp_port = 587
        imap_host = imap_user = imap_pass = ""

    if not (use_whatsapp or use_email):
        click.echo(
            "\nWARNING: you turned both WhatsApp and email off. The bot will "
            "claim tickets but won't tell you about it. Re-run setup to enable "
            "at least one channel."
        )

    profile_dir = existing.get("TICKETSWAP_PROFILE_DIR", "./.chromium-profile")
    watches_path = existing.get("WATCHES_PATH", "./watches.json")

    lines = [
        f"WHATSAPP_PHONE={whatsapp_phone}",
        f"WHATSAPP_APIKEY={whatsapp_apikey}",
        f"SMTP_HOST={smtp_host}",
        f"SMTP_PORT={smtp_port}",
        f"SMTP_USER={smtp_user}",
        f"SMTP_PASS={smtp_pass}",
        f"ALERT_TO={alert_to}",
        f"IMAP_HOST={imap_host}",
        f"IMAP_USER={imap_user}",
        f"IMAP_PASS={imap_pass}",
        f"TICKETSWAP_PROFILE_DIR={profile_dir}",
        f"WATCHES_PATH={watches_path}",
    ]
    env_path.write_text("\n".join(lines) + "\n")
    click.echo(f"\nWrote {env_path.resolve()}")
    click.echo("Next: run `python -m ticketswap test-alerts` to confirm channels work,")
    click.echo("then `python -m ticketswap login`.")


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
    """Send a fake-success notification through every configured channel."""
    settings = load_settings()
    subject, text, html, whatsapp = build_messages(
        label="Test Watch",
        cart_url="https://www.ticketswap.com/",
        listing_url="https://www.ticketswap.com/",
        kind="reservation",
        message="Test - no real reservation happened.",
    )
    subject = "[TEST] " + subject

    if settings.email_enabled:
        click.echo(f"Email    -> {settings.alert_to}")
        try:
            send_alert(settings, subject, text, html)
            click.echo("  ok")
        except Exception as e:
            click.echo(f"  FAILED: {e}")
    else:
        click.echo("Email    -> skipped (not configured)")

    if settings.whatsapp_enabled:
        click.echo(f"WhatsApp -> +{settings.whatsapp_phone}")
        try:
            send_whatsapp(
                settings.whatsapp_phone,
                settings.whatsapp_apikey,
                "[TEST] " + whatsapp,
            )
            click.echo("  ok")
        except Exception as e:
            click.echo(f"  FAILED: {e}")
    else:
        click.echo("WhatsApp -> skipped (not configured)")

    if not (settings.email_enabled or settings.whatsapp_enabled):
        click.echo(
            "\nNothing was sent because no channel is configured. "
            "Run `python -m ticketswap setup`."
        )


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
