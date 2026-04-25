# CLAUDE.md

Notes for future Claude sessions working in this repo.

## What this is

Local Python CLI that watches one or more TicketSwap event URLs, races to
click "Add to cart" (or "Join raffle") the second a ticket appears, and
notifies the user via email + ntfy push so they can finish manual checkout
within the cart-hold window. Personal use, no hosting, no auth.

`PLAN.md` (committed at the root) is the authoritative design doc — read it
first if asked to extend the bot. It also documents the ToS / KYC risks the
user has accepted.

## Dev commands

```bash
# Run from repo root, with a venv active.
pip install -e ".[dev]"           # install + dev deps (pytest, ruff)
playwright install chromium       # one-time Chromium download

pytest -v                          # 19 tests, runs in <1s
ruff check .                       # lint (CI runs both)

python -m ticketswap --help        # CLI surface
```

CI: `.github/workflows/tests.yml` runs `ruff check` then `pytest -v` on push
to `main` and on every PR. Both must stay green.

## Layout

```
ticketswap/
  __main__.py        `python -m ticketswap` entry
  cli.py             setup, login, test, test-alerts, run, list, add, remove
  config.py          .env loader, Settings dataclass, Watch dataclass + JSON load
  claimer.py         Playwright claim flow: open URL, find buy/raffle, click, screenshot
  login.py           One-time interactive login (persistent Chromium profile)
  poller.py          Cheap anonymous availability check (httpx GET + heuristic)
  imap_listener.py   IMAP IDLE listener for TicketSwap alert emails
  matcher.py         URL helpers: event-id parsing, alert -> watch matching
  notifier.py        SMTP email; build_messages() builds (subject, text, html, whatsapp)
  whatsapp.py        WhatsApp via CallMeBot's free gateway
  runner.py          Threading: per-watch poller + IMAP loop, claim mutex, notify on success
tests/               pytest unit tests (matcher, poller, config, notifier)
web/
  app.py             FastAPI setup-wizard (form -> zip download)
  templates/         Jinja2 HTML for the form + install steps
  Dockerfile         Cloud Run image
  README.md          deploy instructions
  tests/             pytest tests for the wizard
PLAN.md              design doc (risks, tradeoffs, build phases)
README.md           non-technical user guide
```

The wizard runs **separately** on Cloud Run and never logs in to
TicketSwap or runs the bot. It only generates `.env` + `watches.json` +
`INSTALL.txt` for the user to download and use locally. Centralising
the bot itself was explicitly rejected (ToS, IP burn, credential
liability); see `PLAN.md` if asked to revisit.

## Architecture quick reference

**Two trigger paths, one claim path.**

```
Trigger paths:
  poller (per-watch thread)  ─┐
                              ├─> _try_claim ─> claim_url (Playwright)
  IMAP IDLE listener (1 thr) ─┘                          │
                                                          ├─> success?
                                                          │   ├─ yes ─> email + ntfy
                                                          │   └─ no  ─> log only
```

- `_claim_lock` (module-level Lock) serializes claim attempts; the persistent
  Chromium profile is single-use.
- Per-watch cooldown (`watch.cooldown_seconds`, default 600s) prevents
  re-firing on the same listing.
- Poller backs off 5 min on `403`/`429` (Cloudflare).

**Watch modes** (`fcfs` / `raffle` / `auto`): control which locator the
claimer tries. `auto` (default) tries buy first, then raffle.

**Mobile delivery**: TicketSwap's cart is account-bound, so phone can finish
payment if logged into the same account. **WhatsApp is the recommended
primary channel** (via CallMeBot's free gateway) because it's universal in
Belgium / NL and needs no SMTP password from the user. **Email is optional
backup** — `Settings.email_enabled` and `Settings.whatsapp_enabled`
properties gate each. The runner emails / WhatsApps independently on
success; one channel's failure doesn't block the other. If neither is
configured, the runner logs a warning and the user is told to re-run
setup.

## Hard constraints

These were all explicitly chosen — don't change without asking the user:

1. **No payment automation.** Bot stops at cart/raffle entry. Human in the
   loop, lower ToS exposure. Don't add card-fill / 3DS-script logic.
2. **No CAPTCHA bypass.** If we hit one, the runner backs off and logs.
   Don't add captcha-solving services.
3. **No aggressive polling.** Default 60s + jitter. Don't lower below ~30s
   without strong reason (Cloudflare 1015 / account ban risk).
4. **No credentials in committed files.** `.env` is gitignored;
   `.env.example` uses placeholders only. Personal email and WhatsApp
   number go in via the interactive `setup` prompt.
5. **Locators stay role/text-based, not class-based.** TicketSwap uses
   hashed CSS classes that change. See `BUY_TEXT` / `RAFFLE_TEXT` regexes
   and `_first_visible` strategy in `claimer.py`.

## Known gaps

- **`Watch.quantity` is stored but not used to filter listings.** Wiring
  this up reliably needs the live DOM (multi-listing pages). User has
  acknowledged this.
- **Claimer locator selectors are educated guesses** — not validated against
  the live TicketSwap DOM. First real run with `test --headed` may need a
  small tweak; the screenshot in `./shots/` is the diagnostic.

## Conventions

- Type hints everywhere (`from __future__ import annotations`).
- `dataclasses` for config / result objects.
- Stdlib `smtplib` for email (no extra deps for SMTP).
- `httpx` for HTTP (already in deps; don't add `requests`).
- One feature per commit; commit messages explain the *why*.
- New CLI commands: add Click decorators in `cli.py`, keep the command body
  small and delegate to the relevant module.
- New config fields: add to `Settings` in `config.py` with a sensible
  default; surface through `setup` if user-facing.

## Testing strategy

- **Unit tests** cover URL/HTML/config helpers — fast, deterministic.
- **Playwright claimer is intentionally not unit-tested** — the live DOM is
  the only honest test. User runs `python -m ticketswap test <url> --headed`
  on a known-available listing to validate.
- **Channels**: `python -m ticketswap test-alerts` sends a fake-success
  email + ntfy push so the user can confirm SMTP / NTFY_URL work without
  needing a real claim.
