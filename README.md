# TicketSwap reservation sniper

A small local Python tool. Watches one or more TicketSwap event URLs, races to
click "Add to cart" (or "Join raffle") the second a ticket appears, and emails
you so you can finish manual checkout within the cart-hold window.

> **Heads up.** Automated access is against TicketSwap's Terms of Service. Use
> at your own risk; KYC means a banned account is hard to replace. Read
> [`PLAN.md`](./PLAN.md) before running.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium
```

## First-time setup

```bash
python -m ticketswap setup
```

Walks you through writing a local `.env`:

- **SMTP** (where alert emails are sent FROM). For Gmail, enable 2FA and
  create an [App Password](https://myaccount.google.com/apppasswords); use it
  as `SMTP_PASS`.
- **Alert recipient** (where alerts go). Defaults to the SMTP user; can be a
  different address (this is what the prompt is for - one tool, multiple
  users, each with their own inbox).
- **IMAP** (optional). If you also turn on TicketSwap's official "Ticket
  alerts" for your event, this listens to those emails via IMAP IDLE and
  fires the claimer the second they arrive - lower footprint than polling.
- **ntfy.sh push** (optional, recommended for mobile). Free, no account.
  Pick a long random topic name in setup, install the
  [ntfy app](https://ntfy.sh/) on your phone, and subscribe to the same
  topic. When a claim succeeds, your phone gets an instant notification
  with an "Open cart" button that deep-links into the TicketSwap app.

Then log in once:

```bash
python -m ticketswap login
```

A Chromium window opens. Log in to TicketSwap, return to the terminal, press
Enter. Cookies are saved to `./.chromium-profile/`. **Don't share that
folder** - it's an active session.

## Add a watch and run

```bash
python -m ticketswap add \
  "https://www.ticketswap.com/concert-tickets/rosalia-antwerp-afas-dome-2026-04-27-CVoAVJWtL6zMBsyXm3fYp" \
  --label "Rosalia Antwerp" \
  --max-price 200 \
  --quantity 1 \
  --mode auto \
  --poll 60

python -m ticketswap list
python -m ticketswap run
```

Options:

| Flag | What it does |
|---|---|
| `--label` | Human-readable name (used in email subject). |
| `--max-price` | Skip if the cheapest visible listing is over this price (EUR). |
| `--quantity` | Number of tickets you want. **Stored but not yet used to filter listings** - implementing this needs the live DOM, see PLAN.md. |
| `--mode fcfs` | Only click buy/reserve. |
| `--mode raffle` | Only click join-raffle / waiting-list. |
| `--mode auto` | Try buy first, fall back to raffle (default). |
| `--poll` | Polling interval in seconds. `0` = IMAP-only. |

`run` starts:

- a polling thread per watch with `--poll > 0` (cheap anonymous GET; the
  heavyweight Playwright claim only fires when the HTML hints availability),
  and
- an IMAP IDLE listener if you configured one in `setup`.

**Emails.** You only get an email if the claim **succeeds** - i.e. you
actually landed in cart/checkout for FCFS, or in the raffle confirmation
page. If someone else was quicker, the bot logs the miss and saves the
screenshot to `./shots/` for debugging, but doesn't email.

- Reservation success → subject `[RESERVED] <label>` → finish payment within
  ~10 minutes.
- Raffle entered → subject `[RAFFLE ENTERED] <label>` → wait for the result
  from TicketSwap.

## Smoke test (no email)

```bash
python -m ticketswap test "<some-currently-available-listing>" --headed
```

Opens the URL with your saved session, tries the click flow, prints the
result, saves a screenshot. **Run this once before relying on `run`** - if
the locator misses, the screenshot tells us what to adjust in
`ticketswap/claimer.py` (`BUY_TEXT`, `RAFFLE_TEXT`, or the locator
fallbacks).

## Files

```
ticketswap/
  cli.py             setup, login, test, run, list, add, remove
  config.py          .env + watches.json loader; Watch dataclass
  claimer.py         Playwright: open URL, find buy/raffle button, click
  login.py           One-time interactive login that persists cookies
  poller.py          Cheap anonymous availability check
  imap_listener.py   IMAP IDLE listener for TicketSwap alert emails
  matcher.py         Match alert URLs to watches by event id
  notifier.py        SMTP email (mobile-friendly HTML + plain text)
  push.py            ntfy.sh push notification sender
  runner.py          Main loop wiring everything together
tests/               Unit tests for the URL/HTML/config helpers
PLAN.md              Design doc + risks + open questions
```

## Finishing payment from your phone

TicketSwap's cart is account-bound, not session-bound: when the bot reserves
on your laptop, the ticket sits in *your account's* cart server-side, and
any device logged into the same account can complete payment.

So once you get the email or ntfy push:

1. Tap the cart link / "Open cart" button.
2. The TicketSwap app (or mobile browser, logged into the same account)
   shows the ticket waiting.
3. Pay with your saved payment method. Done.

Do this **before** you need it: install the TicketSwap app on your phone,
log in, and save a payment method (card, iDEAL, Bancontact). Then the
phone path is one tap → pay.

## What this does not do

- **Doesn't pay.** Intentional. Human in the loop, lower ToS exposure.
- **Doesn't filter listings by quantity yet.** The field is stored; the
  selection logic needs the live DOM.
- **Doesn't bypass CAPTCHAs.** If you hit a Cloudflare challenge, polling
  backs off; log in fresh.
- **Doesn't change raffle odds.** Speed doesn't help in raffles - the bot
  just enters quickly so you don't forget.

See [`PLAN.md`](./PLAN.md) for full architecture, risks, and tradeoffs.
