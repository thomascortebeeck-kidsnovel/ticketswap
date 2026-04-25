# TicketSwap reservation sniper

A small local Python tool. Watches one or more TicketSwap event URLs, races to
click "Add to cart" the second a ticket appears, and emails you so you can
finish the manual checkout within the cart-hold window.

> **Heads up.** Automated access is against TicketSwap's Terms of Service. Use
> at your own risk; KYC means a banned account is hard to replace. Read
> [`PLAN.md`](./PLAN.md) before running.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium
cp .env.example .env  # then edit SMTP/IMAP creds
cp watches.example.json watches.json  # then edit the URL/label
```

## One-time login

```bash
python -m ticketswap login
```

A Chromium window opens. Log in to TicketSwap, then return to the terminal and
press Enter. Cookies are saved to `./.chromium-profile/`. **Don't share that
folder.**

## Smoke test (no email)

```bash
python -m ticketswap test "<ticketswap-url>" --headed
```

Opens the URL with your saved session, tries to click the buy button, and
saves a screenshot to `./shots/`. Run this against a known-available listing
once to verify the locator works on the current TicketSwap DOM. If it doesn't
find the button, check the screenshot and adjust `BUY_TEXT` /
`_find_buy_locator` in `ticketswap/claimer.py`.

## Add a watch and run

```bash
python -m ticketswap add \
  "https://www.ticketswap.com/concert-tickets/rosalia-antwerp-afas-dome-2026-04-27-CVoAVJWtL6zMBsyXm3fYp" \
  --label "Rosalia Antwerp" --max-price 200 --poll 60

python -m ticketswap list
python -m ticketswap run
```

`run` starts:
- a polling thread per watch with `polling_seconds > 0` (cheap anonymous GET,
  Playwright fires only when the HTML hints availability), and
- an IMAP IDLE listener if `IMAP_HOST` is set, which reacts to TicketSwap
  alert emails (faster than polling).

On a successful claim, you get an email with the cart URL and a screenshot.
Finish payment in TicketSwap within ~10 minutes.

## Files

```
ticketswap/
  cli.py             CLI entry: login, test, run, list, add, remove
  config.py          .env + watches.json loader
  claimer.py         Playwright: open URL, find buy button, click, screenshot
  login.py           One-time interactive login that persists cookies
  poller.py          Cheap anonymous availability check
  imap_listener.py   IMAP IDLE listener for TicketSwap alert emails
  matcher.py         Match alert URLs to watches by event id
  notifier.py        SMTP email sender
  runner.py          Main loop wiring everything together
tests/               Unit tests for the URL/HTML helpers
PLAN.md              Design doc + risks + open questions
```

## Testing the locator

You can't realistically test the full flow without a live event. Two options:

1. **Static HTML fixtures.** Save a real ticket-listing page (browser → "Save
   page as") in two states - "no tickets" and "ticket available" - and serve
   them with `python -m http.server`. Point the claimer at `localhost`.
2. **Low-stakes live event.** Pick a cheap event and run `test` against it.
   If reservation succeeds, just don't pay - the listing returns to the pool
   when the cart times out.

## What this does not do

- **Doesn't pay.** Intentionally. Human in the loop, both for safety and to
  stay further from "fully automated buyer".
- **Doesn't bypass CAPTCHAs.** If you hit a Cloudflare challenge, polling
  backs off automatically; you'll need to log in fresh.
- **Doesn't help in raffles.** Speed doesn't matter there - skip those.

See [`PLAN.md`](./PLAN.md) for full architecture and tradeoffs.
