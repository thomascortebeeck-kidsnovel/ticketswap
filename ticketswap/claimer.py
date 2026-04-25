from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import (
    Page,
    TimeoutError as PWTimeoutError,
    sync_playwright,
)

from .config import Settings

# First-come-first-served: buy / add to cart / reserve buttons.
BUY_TEXT = re.compile(
    r"\b(buy(?:\s+ticket)?|add to cart|reserve|koop(?:\s+ticket)?|kopen|"
    r"acheter|kaufen|comprar)\b",
    re.IGNORECASE,
)

# Raffle / waiting list buttons. Speed doesn't help in raffles - we still
# enter so the user has a shot.
RAFFLE_TEXT = re.compile(
    r"\b(join (the )?raffle|enter (the )?raffle|join (the )?waiting list|"
    r"meld(?: je)? aan|wachtlijst|loterij|tirage(?: au sort)?|verlosung)\b",
    re.IGNORECASE,
)

# A successful reservation lands on cart/checkout.
CART_PATH_RE = re.compile(r"/(cart|checkout|reservation|order)\b", re.IGNORECASE)
# Raffle entry lands on a confirmation/queue page.
RAFFLE_PATH_RE = re.compile(r"/(raffle|waiting[-_]?list|queue|wachtlijst)\b", re.IGNORECASE)


@dataclass
class ClaimResult:
    success: bool
    message: str
    kind: str | None = None  # "reservation" | "raffle" | None
    final_url: str | None = None
    screenshot: Path | None = None


def _first_visible(page: Page, locators: list) -> object | None:
    for loc in locators:
        try:
            first = loc.first
            if first.is_visible(timeout=1500):
                return first
        except (PWTimeoutError, Exception):
            continue
    return None


def _find_buy_locator(page: Page):
    return _first_visible(page, [
        page.get_by_role("link", name=BUY_TEXT),
        page.get_by_role("button", name=BUY_TEXT),
        page.locator('a[href*="/buy"]'),
        page.locator('a[href*="/checkout"]'),
        page.locator("button", has_text=BUY_TEXT),
    ])


def _find_raffle_locator(page: Page):
    return _first_visible(page, [
        page.get_by_role("link", name=RAFFLE_TEXT),
        page.get_by_role("button", name=RAFFLE_TEXT),
        page.locator('a[href*="raffle"]'),
        page.locator('a[href*="waiting"]'),
        page.locator("button", has_text=RAFFLE_TEXT),
    ])


def _parse_listed_price_eur(page: Page) -> float | None:
    try:
        text = page.locator("body").inner_text(timeout=2000)
    except PWTimeoutError:
        return None
    prices = []
    for m in re.finditer(r"€\s*([0-9]+(?:[.,][0-9]{1,2})?)", text):
        try:
            prices.append(float(m.group(1).replace(",", ".")))
        except ValueError:
            pass
    return min(prices) if prices else None


def claim_url(
    settings: Settings,
    url: str,
    max_price_eur: float | None = None,
    mode: str = "auto",
    quantity: int | None = None,  # noqa: ARG001 - reserved for future DOM-aware filtering
    headless: bool = True,
) -> ClaimResult:
    """Open URL in the persistent profile, click buy or join-raffle, screenshot.

    Modes:
        "fcfs"   - only try the buy/reserve button
        "raffle" - only try the join-raffle button
        "auto"   - try buy first, fall back to raffle (default)

    `quantity` is currently informational. Listing-quantity filtering needs the
    live DOM to implement reliably; see PLAN.md.

    Does not complete payment - intentionally manual.
    """
    settings.profile_dir.mkdir(parents=True, exist_ok=True)
    settings.shots_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(settings.profile_dir),
            headless=headless,
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        try:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=12_000)
            except PWTimeoutError as e:
                shot = settings.shots_dir / f"timeout-{ts}.png"
                _safe_screenshot(page, shot)
                return ClaimResult(False, f"goto timeout: {e}", None, page.url, shot)

            if mode in ("fcfs", "auto") and max_price_eur is not None:
                listed = _parse_listed_price_eur(page)
                if listed is not None and listed > max_price_eur:
                    shot = settings.shots_dir / f"overprice-{ts}.png"
                    _safe_screenshot(page, shot)
                    return ClaimResult(
                        False,
                        f"Cheapest listed €{listed:.2f} > max €{max_price_eur:.2f}; skipping",
                        None,
                        page.url,
                        shot,
                    )

            target = None
            kind: str | None = None
            if mode == "fcfs":
                target, kind = _find_buy_locator(page), "reservation"
            elif mode == "raffle":
                target, kind = _find_raffle_locator(page), "raffle"
            else:  # auto
                target = _find_buy_locator(page)
                if target:
                    kind = "reservation"
                else:
                    target = _find_raffle_locator(page)
                    if target:
                        kind = "raffle"

            if not target:
                shot = settings.shots_dir / f"miss-{ts}.png"
                _safe_screenshot(page, shot)
                return ClaimResult(
                    False, f"No matching button visible (mode={mode})", None, page.url, shot
                )

            try:
                target.click(timeout=3_000)
            except PWTimeoutError as e:
                shot = settings.shots_dir / f"clickfail-{ts}.png"
                _safe_screenshot(page, shot)
                return ClaimResult(False, f"click timeout: {e}", kind, page.url, shot)

            try:
                page.wait_for_load_state("domcontentloaded", timeout=6_000)
            except PWTimeoutError:
                pass

            shot = settings.shots_dir / f"hit-{ts}.png"
            _safe_screenshot(page, shot)

            success = False
            message = "Clicked but outcome unconfirmed"
            if kind == "reservation":
                success = bool(CART_PATH_RE.search(page.url))
                message = "Reserved - in cart/checkout" if success else "Click landed but no cart URL"
            elif kind == "raffle":
                success = bool(RAFFLE_PATH_RE.search(page.url))
                message = "Entered raffle" if success else "Raffle click landed but unconfirmed"

            return ClaimResult(success, message, kind, page.url, shot)
        finally:
            ctx.close()


def _safe_screenshot(page: Page, path: Path) -> None:
    try:
        page.screenshot(path=str(path), full_page=True)
    except Exception:
        pass
