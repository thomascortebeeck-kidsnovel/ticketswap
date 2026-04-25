# TicketSwap Sniper — Plan

A small local app that watches one or more TicketSwap event/type URLs and, the
moment a new ticket appears, **reserves it (adds to cart)** and emails the
user so they can finish the manual checkout within the cart-hold window.

> Personal use only, run locally, no auth, no public hosting.

---

## 1. Read this first — risks & legal/ToS reality

TicketSwap actively fights bots. Before building anything, the user should
understand the tradeoffs:

- **Terms of Service.** Automated access / scraping is against TicketSwap's
  ToS. Detected accounts get banned and KYC means a banned account is hard to
  replace.
- **Anti-bot stack.** Cloudflare, CAPTCHAs on suspicious traffic, KYC on
  signup, 8-ticket purchase cap per event, and ongoing patches against
  publicly known bots (e.g. the Android `AccessibilityService` approach was
  patched after the Medium write-up).
- **Ethical note.** Ticket alerts are explicitly first-come-first-served. A
  faster-than-human bot disadvantages other fans buying for themselves.
- **Speed ceiling.** TicketSwap's own push notifications fire "the second a
  new ticket is listed". Beating that materially requires either (a) reacting
  to the push *before* a human can tap it, or (b) hammering the page faster
  than Cloudflare tolerates. (a) is what we should target.

**Strongly recommended baseline before building anything custom:** turn on
TicketSwap's official **Ticket Alerts** and, if available for the event, the
official **Auto buy tickets** feature. They already solve the problem for
most events without ToS risk. The custom bot is only worth building if those
fail for a specific event (e.g. Auto-buy not offered, or user wants per-link
price caps and custom routing).

The plan below assumes the user accepts the above and wants the tool anyway.

---

## 2. How TicketSwap actually works (relevant bits)

- **Event → ticket-type pages.** Each event has a city/venue-specific URL
  (e.g. `ticketswap.com/event/<slug>/<type-id>`). Tickets list under a
  specific type/category. We'll subscribe per URL — one per event/city/type.
- **Listings appear instantly** when a seller uploads a ticket. The page goes
  from "no tickets" to a "Buy"/"Add to cart" button on the new listing.
- **Reservation, not purchase, is the race.** Clicking the buy button locks
  the ticket in your cart for a short window (~10 min historically). Payment
  is completed afterwards. Our bot's job is **win the reserve race** — the
  user finishes payment by hand.
- **Two sale modes.**
  - *First-come-first-served:* fastest click wins. This is what we optimize
    for.
  - *Raffle / waiting list:* you enter a draw; speed doesn't help. The bot
    can still auto-enter the raffle on detection but it won't change odds.
- **Official auto-buy** queues users by signup time, not click time, and
  needs a saved payment method + max budget. Where it exists, it's a strict
  upgrade over a bot.

---

## 3. Goals (scope)

In scope:
1. Add a "watch" by pasting a TicketSwap ticket-type URL + max price.
2. Detect new tickets fast and reliably.
3. Auto-click "Add to cart" / "Buy" / "Reserve" using a logged-in browser
   session.
4. Email the user the moment a ticket is reserved.
5. Per-link config (city = different URL = separate watch).
6. Run locally on the user's laptop. No hosting, no accounts.

Out of scope:
- Auto-completing payment (intentional — leave human in the loop, both for
  safety and to stay further from "fully automated buyer").
- Multi-user / web UI / auth.
- Defeating CAPTCHAs.
- Raffle odds manipulation.

---

## 4. Architecture — two viable approaches, pick one

### Approach A (recommended): notification-driven

Goal: react to TicketSwap's *own* push/email alert instead of polling the
site. Lowest detection footprint, fastest reaction.

```
TicketSwap email alert ──▶ IMAP IDLE listener ──▶ Match watch (URL/event)
                                                       │
                                                       ▼
                                         Headless browser w/ saved session
                                                       │
                                                       ▼
                                       Open URL → click "Add to cart"
                                                       │
                                                       ▼
                                  Email user "RESERVED — pay within 10 min"
```

Pros: piggybacks on TicketSwap's own infra, polling rate = 0, minimal
Cloudflare exposure.
Cons: bounded by how fast TicketSwap fires the alert; email/IMAP latency
adds seconds; first humans on push are still close in time.

### Approach B (fallback): polite polling

If Auto-buy and alerts aren't enough for a specific event, poll the
ticket-type URL on a **slow** schedule (e.g. 30–120s with jitter) per watch.
Existing OSS projects use 10 min as a "safe" floor — we can be faster but
must back off on 403/429/CAPTCHA.

Pros: works without alerts, no email plumbing.
Cons: high Cloudflare risk, slower than notification-driven if you stay
polite, fast polling will get the account/IP flagged.

### Recommendation
Build A as the primary path. Keep B as an opt-in supplement per watch (off
by default). Both share the same "claim" stage (browser automation).

---

## 5. Components

| Component | Job | Tech |
|---|---|---|
| `watches.json` (or sqlite) | List of watches: URL, max price, label | Plain file, no DB needed for v1 |
| **Notifier listener** | IMAP IDLE on the user's inbox; parses TicketSwap alert mails; emits "new ticket" events tagged with event/URL | Python `imap-tools` or Node `imapflow` |
| **Poller** (optional) | Fetches watched URLs on a slow schedule with jitter + exponential backoff on 403/429 | Same runtime as listener |
| **Claimer** | Headless browser with persistent profile (already logged into TicketSwap). Opens the URL, finds the buy button, clicks it, screenshots the result | Playwright (Chromium, persistent context) |
| **Alerter** | On successful reserve, send email (and optionally desktop notification + sound) | SMTP (Gmail app password) + `node-notifier`/`plyer` |
| **CLI** | `add <url> --max-price 80 --label "Rosalia Antwerp"`, `list`, `remove`, `run` | Click / Commander |

**Single process, single language.** Pick one stack — Python (Playwright +
imap-tools + smtplib) is the cleanest fit; Node (Playwright + imapflow +
nodemailer) is equally fine. No need for a queue, DB, or web server in v1.

---

## 6. Claimer — how the click actually happens

The fragile part. Plan:

1. **One-time login.** User runs `npm run login` / `python -m app.login`,
   which opens a real Chromium window via Playwright with a persistent user
   data dir. They log in by hand (handles SSO/2FA/CAPTCHA). Session cookies
   persist on disk.
2. **Locator strategy.** Don't hard-code CSS class names (Cloudflare-style
   hashed classnames change). Prefer:
   - `getByRole('link', { name: /buy|add to cart|reserve/i })`
   - Fallback: any `<a href*="/buy"` or button with i18n text matching a
     short list (`Buy`, `Koop`, `Kopen`, `Acheter`, etc.).
3. **Race-safe click.** `page.goto(url, { waitUntil: 'domcontentloaded' })`
   → wait for the buy locator with a tight timeout (e.g. 4s) → `click`.
   On any timeout, capture HTML + screenshot for debugging.
4. **Confirm reservation.** Look for the cart/checkout URL or a "Reserved"
   indicator before declaring success. If not found, treat as failure and
   alert with the screenshot anyway so the user can decide.
5. **No retries on failure** for the same listing (it's gone). Continue
   watching for the next one only if the watch is still active.

---

## 7. Alerter — what the email says

Subject: `🎟  Reserved: <label> — pay within 10 min`
Body:
- Event label, URL, listed price.
- Direct link to TicketSwap cart.
- Timestamp + a hard "deadline" (now + 10 min, conservative).
- Attached screenshot of the reservation page.

Email-only (per the user's spec). SMTP via Gmail app password is the
shortest path; no third-party service needed.

---

## 8. Configuration

`watches.json` (v1):
```json
[
  {
    "label": "Rosalia — Antwerp",
    "url": "https://www.ticketswap.com/event/.../...",
    "max_price_eur": 90,
    "active": true,
    "polling_seconds": 0
  }
]
```
- `polling_seconds: 0` → notification-driven only (Approach A).
- `> 0` → also poll at that cadence (Approach B).
- `max_price_eur` is enforced by reading the listing price *before* clicking;
  if the page parses cleanly and price > max, skip. If price can't be parsed
  in time, default to **claim anyway** (reserving a too-expensive ticket
  costs nothing — you just don't pay).

`.env`:
```
SMTP_HOST=…
SMTP_USER=…
SMTP_PASS=…
ALERT_TO=…
IMAP_HOST=…
IMAP_USER=…
IMAP_PASS=…
TICKETSWAP_PROFILE_DIR=./.chromium-profile
```

---

## 9. Build phases

**Phase 0 — sanity check (no code).** Have the user enable TicketSwap's
official Ticket Alerts and, if offered, Auto buy tickets, for the specific
event(s) they care about. If that solves it, stop.

**Phase 1 — manual claimer.** Playwright script: `claim <url>` → opens URL
in persistent profile, clicks the buy button, screenshots. No watching
yet. Validates the locator strategy on a real, low-stakes event.

**Phase 2 — IMAP listener.** Subscribe to TicketSwap alert emails on the
user's inbox, parse them, fire claimer. End-to-end on a real alert.

**Phase 3 — watches + alerter.** `watches.json`, CLI, success/failure email.

**Phase 4 — polite poller (optional).** Only if Phase 1–3 misses tickets.
Hard cap polling rate, exponential backoff on 403/429, abort on CAPTCHA
challenge.

**Phase 5 — UX polish.** Desktop notification + sound on success; structured
logs; re-login helper when cookies expire.

Each phase is independently useful — stop at the earliest one that wins
tickets.

---

## 10. Testing strategy

The hard problem: we can't easily reproduce "new ticket appears" on demand
without messing with TicketSwap. Options:

1. **Static HTML fixtures.** Snapshot a real ticket-listing page in both
   "no tickets" and "one ticket available" states; serve them locally; point
   the claimer at `localhost`. Verifies locator + click logic offline.
2. **Low-stakes live event.** Pick an event with cheap, frequently-listed
   tickets and dry-run the full flow with claim → cancel.
3. **Rate-limit canary.** Before pointing real polling at TicketSwap,
   measure response codes from a single sequential GET loop and watch for
   the first 403/429.

---

## 11. Failure modes & how we handle them

| Failure | Handling |
|---|---|
| Cookies expired | Claimer detects redirect to login; sends "re-login needed" email; halts watches until user re-runs login flow |
| Cloudflare CAPTCHA | Detect challenge HTML; skip click; back off poller; email user |
| Buy button selector changed | Locator falls through to text-match list; if all miss, screenshot + email "DOM change, please update" |
| Two watches fire at once | Single in-flight claim per browser context; serialize with a mutex |
| Email alert arrives after the ticket is gone | Claimer reports "no buy button found within 4s" → email "alert seen but ticket gone" |
| Account banned | Bot stops; nothing we can do programmatically |

---

## 12. Open questions for the user

1. Email-only on success, or also desktop notification + sound? (Plan
   defaults to email-only per request; sound is nearly free to add.)
2. Should the bot enforce `max_price_eur` strictly, or always claim and let
   the user decide at checkout? (Plan: parse price; if not parseable in
   time, claim anyway.)
3. Python or Node? (Plan defaults to Python; equally happy with Node.)
4. For raffles: auto-enter, or skip? (Plan: skip in v1 — entering doesn't
   help you win and adds API surface to maintain.)
5. Is the user OK pre-saving a Gmail app password locally, or do they want
   a different SMTP provider?

---

## 13. TL;DR

- **First, try TicketSwap's own Ticket Alerts + Auto-buy.** They're the
  intended solution and don't risk a ban.
- If that's not enough, build a small Python+Playwright tool: IMAP-IDLE
  listener on TicketSwap alert emails → headless browser with a saved
  logged-in session → clicks "Add to cart" → emails the user to finish
  payment. ~few hundred lines of code, single process, runs on the laptop.
- Avoid aggressive polling. It loses to TicketSwap's own push, gets your
  IP/account flagged, and is the part of every public bot that gets patched.
