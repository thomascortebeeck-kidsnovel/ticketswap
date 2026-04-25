from __future__ import annotations

from playwright.sync_api import sync_playwright

from .config import Settings


def do_login(settings: Settings) -> None:
    """One-time interactive login. Saves cookies to the persistent profile."""
    settings.profile_dir.mkdir(parents=True, exist_ok=True)
    print(f"Opening Chromium with profile: {settings.profile_dir.resolve()}")
    print("Log in to TicketSwap in the browser window, then return here.")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(settings.profile_dir),
            headless=False,
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        page.goto("https://www.ticketswap.com/login", wait_until="domcontentloaded")
        try:
            input("Press Enter once you're logged in (look for your avatar)... ")
        finally:
            ctx.close()
    print(f"Session saved at {settings.profile_dir}.")
