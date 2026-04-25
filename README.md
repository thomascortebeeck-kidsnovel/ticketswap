# TicketSwap helper

A small program that runs on your computer and watches a TicketSwap event
page for you. The moment a ticket appears, it clicks "Add to cart" so the
ticket lands in your basket. It then sends you a **WhatsApp message** (and
optionally an email) so you can finish paying — even if you're not at home.

**You still pay manually**. The program only races to grab the ticket
before someone else does.

> ⚠️ **Heads up — please read.** Using bots on TicketSwap is against their
> Terms of Service. They can ban your account, and because they verify
> identity (KYC), getting a new account is hard. This is for personal use,
> at your own risk.

---

## What you'll need

1. **A computer** that can stay turned on (Mac, Windows, or Linux).
2. **A TicketSwap account** — sign up at https://www.ticketswap.com/.
3. **A phone with WhatsApp** — that's how you'll get notified.
4. **The TicketSwap app** on your phone (so you can pay quickly when alerted).
5. **About 15 minutes** the first time. After setup, starting it again
   takes 10 seconds.

Email alerts are **optional** and turned off by default. If you want them
as a backup, you'll also need a Gmail account.

---

## Step 1 — Open a terminal

The "terminal" is a window where you type commands. You only type a few.

### macOS
1. Press `Cmd + Space`, type `Terminal`, press Enter.

### Windows
1. Press the Windows key, type `PowerShell`, press Enter.

### Linux
You already know.

> 💡 **Copy/paste tip.** Click inside a grey box, select all, copy
> (Ctrl/Cmd + C), paste into the terminal (Ctrl/Cmd + V on Mac;
> right-click on Windows). Press Enter to run.

---

## Step 2 — Install Python (if you don't have it)

In the terminal:

```bash
python3 --version    # macOS / Linux
python --version     # Windows
```

If it prints `Python 3.11` or higher, skip ahead. Otherwise install from
https://www.python.org/downloads/ — **on Windows, tick "Add python.exe
to PATH" on the first installer screen**.

---

## Step 3 — Download the program

```bash
git clone https://github.com/thomascortebeeck-kidsnovel/ticketswap.git
cd ticketswap
git checkout claude/ticketswap-bot-plan-SMX2r
```

> 💡 If `git` isn't installed: get it from https://git-scm.com/downloads
> with default options, close and reopen the terminal, retry.

---

## Step 4 — Install the program's dependencies

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
```

### Windows (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
playwright install chromium
```

`playwright install chromium` downloads Chromium (~150 MB). Coffee break.

> 💡 Whenever you reopen the terminal later, run the activate line again
> (`source .venv/bin/activate` on Mac/Linux, `.venv\Scripts\Activate.ps1`
> on Windows) before running any `python -m ticketswap …` command. Your
> prompt shows `(.venv)` when it's active.

---

## Step 5 — Get your CallMeBot WhatsApp APIKEY

This is what lets the program send you WhatsApp messages. It's free.

1. On your phone, open
   https://www.callmebot.com/blog/free-api-whatsapp-messages/ — that page
   has the bot's current contact number and a copy-pasteable activation
   message. Follow it exactly:
   - Save the bot's phone number to your contacts.
   - Send the activation WhatsApp message to that contact.
2. Wait for the bot to reply. The reply contains your **APIKEY** —
   a 6–8 digit number. Copy it.
3. You'll also need **your own** WhatsApp number in international format,
   e.g. `+32 472 12 34 56` (Belgium) → enter as `+32472123456` or just
   `32472123456`.

That's it. No account, no password, no setup fee.

---

## Step 6 — Run the setup wizard

```bash
python -m ticketswap setup
```

Answer the prompts:

| Prompt | What to type |
|---|---|
| Configure WhatsApp notifications? | `y` |
| Your WhatsApp number | e.g. `+32472123456` |
| Your CallMeBot APIKEY | the number from Step 5 |
| Configure email alerts? | `n` (or `y` if you want a backup — see below) |

If you said no to email, you're done with setup. **Go to Step 7.**

### Optional: enable email backup

If you said `y` to email, the wizard asks for a Gmail address and an
**App Password** (not your normal Gmail password). Get one at
https://myaccount.google.com/apppasswords (Google account → Security →
2-step verification must be on; App passwords → Mail → Other →
"TicketSwap helper" → Generate). Paste the 16-character password.

It also asks if you want IMAP. Say `y` — it lets the program react to
TicketSwap's own alert emails the second they arrive (faster than just
polling the page).

---

## Step 7 — Test that notifications work

```bash
python -m ticketswap test-alerts
```

You should get within a few seconds:

- ✅ A WhatsApp message saying "[TEST] [RESERVED] Test Watch …"
- ✅ (If email is on) An email with a big blue **Open cart** button.

If it fails, the terminal prints why. Most common issues: typo in
APIKEY or phone number, or you forgot the activation step in Step 5.
Re-run `python -m ticketswap setup` to fix.

---

## Step 8 — Log in to TicketSwap (one time)

```bash
python -m ticketswap login
```

A Chrome window opens. Log in to TicketSwap **with the same account you
use on your phone**. Back to the terminal, press Enter. The window
closes; the program saved your login.

> 🔒 The login is saved in `.chromium-profile/`. Don't share that folder
> — it contains your active TicketSwap session.

---

## Step 9 — Add the event you want

Get the event URL from your browser. For example:

```bash
python -m ticketswap add \
  "https://www.ticketswap.com/concert-tickets/rosalia-antwerp-afas-dome-2026-04-27-CVoAVJWtL6zMBsyXm3fYp" \
  --label "Rosalia Antwerp" \
  --max-price 200 \
  --quantity 1 \
  --mode auto \
  --poll 60
```

| Part | Meaning |
|---|---|
| The URL | Copy from your browser. **Keep the quotes.** |
| `--label` | Any name you'll recognise. |
| `--max-price` | Skip listings cheaper than… nope, *more expensive than* this (€). |
| `--quantity` | How many tickets you want. (Currently informational.) |
| `--mode auto` | Try the regular Buy button first; fall back to Join Raffle. |
| `--poll 60` | Check every 60 seconds. |

Useful:
```bash
python -m ticketswap list             # what's saved
python -m ticketswap remove "Rosalia" # delete by label
```

---

## Step 10 — Start watching

```bash
python -m ticketswap run
```

The terminal prints status lines. **Leave the window open.** When a
ticket appears:

1. The program clicks **Add to cart** on the laptop.
2. Your phone gets a **WhatsApp message** with the cart URL.
3. (Optional) An email arrives with a tap-to-open cart button.
4. Tap the cart link in WhatsApp. The TicketSwap app opens with the
   ticket already in your basket.
5. Pay. Done.

You have **about 10 minutes** before the cart times out and the ticket
goes back to the pool.

To stop: click in the terminal and press `Ctrl + C`.

---

## Before you actually need this — pre-flight checks

Do these once, ahead of the event you care about:

- ✅ Run `python -m ticketswap test-alerts`. WhatsApp arrives on your phone.
- ✅ TicketSwap app installed on your phone, logged into the same account
  the bot uses, with a **payment method** saved (card / iDEAL /
  Bancontact). Otherwise checkout takes too long.
- ✅ WhatsApp notifications allowed when phone is locked.
- ✅ Laptop set to never sleep while the bot runs (you can re-enable
  sleep after).

---

## Troubleshooting

**"command not found: python3 / git"**
You skipped Step 2 / Step 3. Install, close and reopen the terminal,
retry.

**WhatsApp test-alert failed: "CallMeBot rejected the request"**
- Did you actually send the activation message in Step 5? Without that,
  the apikey doesn't work.
- Is the phone number in the right format (digits only, with country
  code, no `+`)?
- Did you copy the APIKEY exactly?

**The browser opens but I get a CAPTCHA**
Solve it manually in the window during `login`. If a CAPTCHA appears
during a real claim, the program backs off. There's no way to bypass it.

**The bot says "no buy button visible" but a ticket is clearly there**
The locator missed. Look at the most recent screenshot in `shots/`.
Open a GitHub issue with the screenshot.

**Email isn't arriving**
You either didn't enable email in setup, or used your real Gmail
password instead of an App Password (Step 6 → optional). Re-run setup.

**Account got banned**
Sorry. Read the warning at the top of this README again before trying
to make a new one.

---

## What this program does NOT do

- It does **not** pay for the ticket. You always do that step.
- It does **not** improve your odds in raffle events (raffles pick
  randomly; speed doesn't help).
- It does **not** bypass CAPTCHAs.
- It does **not** run in the cloud. Your computer has to stay on.

---

## Files in this repo

- `PLAN.md` — design doc with risks and tradeoffs (technical).
- `CLAUDE.md` — notes for AI assistants extending the code.
- `ticketswap/` — the program's source code.
- `tests/` — automated tests.

If something in this guide is unclear, open a GitHub issue.
