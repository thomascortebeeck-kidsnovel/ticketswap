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

# Tries to match the buy/reserve button across the languages TicketSwap ships in.
BUY_TEXT = re.compile(
    r"\b(buy(?:\s+ticket)?|add to cart|reserve|koop(?:\s+ticket)?|kopen|"
    r"acheter|kaufen|comprar)\b",
    re.IGNORECASE,
)

# A clicked listing puts you in the cart/checkout flow.
CART_PATH_RE = re.compile(r"/(cart|checkout|reservation|order)\b", re.IGNORECASE)


@dataclass
class ClaimResult:
    success: bool
    message: str
    final_url: str | None = None
    screenshot: Path | None = None


def _find_buy_locator(page: Page):
    """Try several locator strategies; return the first visible one or None.

    DOM details are intentionally not hard-coded - TicketSwap uses hashed CSS
    classes that change. We rely on role + accessible name, then fall back to
    href/text patterns.
    """
    candidates = [
        page.get_by_role("link", name=BUY_TEXT),
        page.get_by_role("button", name=BUY_TEXT),
        page.locator('a[href*="/buy"]'),
        page.locator('a[href*="/checkout"]'),
        page.locator("button", has_text=BUY_TEXT),
    ]
    for loc in candidates:
        try:
            first = loc.first
            if first.is_visible(timeout=1500):
                return first
        except (PWTimeoutError, Exception):
            continue
    return None


def _parse_listed_price_eur(page: Page) -> float | None:
    """Best-effort scrape of the cheapest visible listing price in EUR."""
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
    headless: bool = True,
) -> ClaimResult:
    """Open URL in the persistent profile, click the buy button, screenshot.

    Does not complete payment - that's intentionally manual.
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
                return ClaimResult(False, f"goto timeout: {e}", page.url, shot)

            if max_price_eur is not None:
                listed = _parse_listed_price_eur(page)
                if listed is not None and listed > max_price_eur:
                    shot = settings.shots_dir / f"overprice-{ts}.png"
                    _safe_screenshot(page, shot)
                    return ClaimResult(
                        False,
                        f"Cheapest listed price €{listed:.2f} > max €{max_price_eur:.2f}; skipping",
                        page.url,
                        shot,
                    )

            buy = _find_buy_locator(page)
            if not buy:
                shot = settings.shots_dir / f"miss-{ts}.png"
                _safe_screenshot(page, shot)
                return ClaimResult(
                    False, "No buy/reserve button visible", page.url, shot
                )

            try:
                buy.click(timeout=3_000)
            except PWTimeoutError as e:
                shot = settings.shots_dir / f"clickfail-{ts}.png"
                _safe_screenshot(page, shot)
                return ClaimResult(False, f"click timeout: {e}", page.url, shot)

            try:
                page.wait_for_load_state("domcontentloaded", timeout=6_000)
            except PWTimeoutError:
                pass  # we still want to screenshot whatever's there

            shot = settings.shots_dir / f"hit-{ts}.png"
            _safe_screenshot(page, shot)

            in_cart = bool(CART_PATH_RE.search(page.url))
            return ClaimResult(
                success=in_cart,
                message=("Reserved - in cart/checkout" if in_cart
                         else "Clicked but reservation unconfirmed"),
                final_url=page.url,
                screenshot=shot,
            )
        finally:
            ctx.close()


def _safe_screenshot(page: Page, path: Path) -> None:
    try:
        page.screenshot(path=str(path), full_page=True)
    except Exception:
        pass
