from __future__ import annotations

import threading
import time
from threading import Event, Lock

from .claimer import ClaimResult, claim_url
from .config import Settings, Watch, load_watches
from .imap_listener import stream_alerts
from .matcher import event_id, match_alert_to_watches
from .notifier import build_messages, send_alert
from .poller import fetch_html, looks_available, sleep_with_jitter
from .whatsapp import send_whatsapp

# Only one Playwright claim runs at a time - the persistent profile is single-use,
# and we don't want two claims fighting over the same browser session.
_claim_lock = Lock()


def run_watch_loop(settings: Settings) -> None:
    watches = load_watches(settings.watches_path)
    if not watches:
        print(f"No watches in {settings.watches_path}. See watches.example.json.")
        return

    active = [w for w in watches if w.active]
    print(f"Loaded {len(active)} active watch(es):")
    for w in active:
        print(f"  - {w.label}  poll={w.polling_seconds}s  max=€{w.max_price_eur}")

    stop = Event()
    cooldowns: dict[str, float] = {}
    cooldown_lock = Lock()

    threads: list[threading.Thread] = []
    for w in active:
        if w.polling_seconds and w.polling_seconds > 0:
            t = threading.Thread(
                target=_poll_loop,
                args=(settings, w, stop, cooldowns, cooldown_lock),
                daemon=True,
                name=f"poll[{w.label}]",
            )
            t.start()
            threads.append(t)

    if settings.imap_host:
        t = threading.Thread(
            target=_imap_loop,
            args=(settings, active, cooldowns, cooldown_lock),
            daemon=True,
            name="imap",
        )
        t.start()
        threads.append(t)
        print(f"IMAP listener started on {settings.imap_host}")
    else:
        print("IMAP not configured; running in polling-only mode.")

    if not threads:
        print("Nothing to do (no IMAP and no watch has polling_seconds > 0).")
        return

    try:
        while not stop.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        stop.set()


def _poll_loop(
    settings: Settings,
    watch: Watch,
    stop: Event,
    cooldowns: dict[str, float],
    cooldown_lock: Lock,
) -> None:
    while not stop.is_set():
        if sleep_with_jitter(watch.polling_seconds, stop):
            return
        if _in_cooldown(watch, cooldowns, cooldown_lock):
            continue
        try:
            status, html = fetch_html(watch.url)
        except Exception as e:
            print(f"[poll] {watch.label}: fetch error {e}")
            continue
        if status in (403, 429):
            print(f"[poll] {watch.label}: status {status} - backing off 5 min")
            stop.wait(300)
            continue
        if status >= 400:
            print(f"[poll] {watch.label}: status {status}")
            continue
        if looks_available(html):
            print(f"[poll] {watch.label}: looks available -> claiming")
            _try_claim(settings, watch, watch.url, cooldowns, cooldown_lock)


def _imap_loop(
    settings: Settings,
    watches: list[Watch],
    cooldowns: dict[str, float],
    cooldown_lock: Lock,
) -> None:
    for alert in stream_alerts(settings):
        print(f"[imap] alert: {alert.subject!r} ({len(alert.urls)} url(s))")
        matches = match_alert_to_watches(alert.urls, watches)
        if not matches:
            print("[imap] no matching watches; ignoring")
            continue
        for w, hit_url in matches:
            if _in_cooldown(w, cooldowns, cooldown_lock):
                print(f"[imap] {w.label}: in cooldown; skipping")
                continue
            _try_claim(settings, w, hit_url, cooldowns, cooldown_lock)


def _in_cooldown(w: Watch, cooldowns: dict[str, float], lock: Lock) -> bool:
    key = event_id(w.url) or w.url
    with lock:
        until = cooldowns.get(key, 0.0)
        return time.time() < until


def _set_cooldown(w: Watch, cooldowns: dict[str, float], lock: Lock) -> None:
    key = event_id(w.url) or w.url
    with lock:
        cooldowns[key] = time.time() + w.cooldown_seconds


def _try_claim(
    settings: Settings,
    watch: Watch,
    url: str,
    cooldowns: dict[str, float],
    cooldown_lock: Lock,
) -> None:
    if not _claim_lock.acquire(blocking=False):
        print(f"[claim] {watch.label}: another claim in flight; skipping")
        return
    try:
        _set_cooldown(watch, cooldowns, cooldown_lock)
        print(f"[claim] {watch.label}: opening {url}")
        result = claim_url(
            settings,
            url,
            max_price_eur=watch.max_price_eur,
            mode=watch.mode,
            quantity=watch.quantity,
        )
        print(f"[claim] {watch.label}: {result.message}")
        if result.success:
            _email_success(settings, watch, url, result)
        else:
            # Someone else was quicker, the page changed, or the locator missed.
            # Don't email - just log + keep the screenshot for debugging.
            shot = result.screenshot
            print(f"[claim] {watch.label}: not emailing (no success). screenshot={shot}")
    finally:
        _claim_lock.release()


def _email_success(
    settings: Settings, watch: Watch, url: str, result: ClaimResult
) -> None:
    cart_url = result.final_url or url
    subject, text, html, whatsapp = build_messages(
        label=watch.label,
        cart_url=cart_url,
        listing_url=url,
        kind=result.kind or "reservation",
        message=result.message,
    )

    if settings.email_enabled:
        try:
            send_alert(settings, subject, text, html, result.screenshot)
            print(f"[email] sent to {settings.alert_to}")
        except Exception as e:
            print(f"[email] failed: {e}")

    if settings.whatsapp_enabled:
        try:
            send_whatsapp(settings.whatsapp_phone, settings.whatsapp_apikey, whatsapp)
            print(f"[whatsapp] sent to +{settings.whatsapp_phone}")
        except Exception as e:
            print(f"[whatsapp] failed: {e}")

    if not (settings.email_enabled or settings.whatsapp_enabled):
        print("[notify] WARNING: no channel configured. Run `python -m ticketswap setup`.")
