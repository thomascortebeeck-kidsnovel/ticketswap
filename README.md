# TicketSwap helper

A small program that runs on your computer and watches a TicketSwap event
page for you. The moment a ticket appears, it clicks "Add to cart" so the
ticket lands in your basket. Then it sends you an email and a notification
on your phone so you can finish paying — even if you're not at home.

**You still pay manually**. The program only races to grab the ticket
before someone else does.

> ⚠️ **Heads up — please read.** Using bots on TicketSwap is against their
> Terms of Service. They can ban your account, and because they verify
> identity (KYC), getting a new account is hard. This is for personal use,
> at your own risk.

---

## What you'll need

1. **A computer** that can stay turned on (Mac, Windows, or Linux).
2. **A TicketSwap account** — sign up at https://www.ticketswap.com/ if
   you haven't.
3. **A Gmail account** for sending the alert emails. Other providers work
   too, but this guide uses Gmail because it's the easiest.
4. **A phone** with internet, the **TicketSwap app**, and the **ntfy app**
   (free, see below).
5. **About 20 minutes** the first time. After setup, starting it again
   takes 10 seconds.

---

## Step 1 — Open a terminal

The "terminal" is a window where you type commands. Don't worry, you only
type a few.

### On macOS

1. Press `Cmd + Space` to open Spotlight.
2. Type `Terminal` and press Enter.

A black or white window opens with a `$` prompt. That's the terminal.

### On Windows

1. Press the Windows key.
2. Type `PowerShell` and press Enter.

A blue window opens. That's the terminal.

### On Linux

You already know.

> 💡 **Copy/paste tip.** When the guide shows a command in a grey box,
> click inside it, select all the text, copy (Ctrl/Cmd + C), then paste
> into the terminal (Ctrl/Cmd + V on Mac; right-click on Windows). Press
> Enter to run.

---

## Step 2 — Install Python

Python is the language this program is written in.

### macOS

Open Terminal and paste this, then press Enter:

```bash
python3 --version
```

- If it prints something like `Python 3.11.5` (anything 3.11 or higher),
  you're done — skip to Step 3.
- If it says "command not found" or shows an older version, install the
  latest Python from https://www.python.org/downloads/ (download the
  installer, double-click it, click Next a few times).

### Windows

Open PowerShell and paste:

```powershell
python --version
```

- If it prints `Python 3.11` or higher, skip to Step 3.
- Otherwise: install Python from https://www.python.org/downloads/. **On
  the first installer screen, tick the box "Add python.exe to PATH" before
  clicking Install.** That's important.

---

## Step 3 — Download the program

In the terminal, paste:

```bash
git clone https://github.com/thomascortebeeck-kidsnovel/ticketswap.git
cd ticketswap
git checkout claude/ticketswap-bot-plan-SMX2r
```

> 💡 If `git` isn't installed: download it from https://git-scm.com/downloads,
> install with the default options, close the terminal, reopen it, and try
> again.

You should now see a list of files when you type `ls` (Mac/Linux) or
`dir` (Windows). Look for `README.md` and a folder called `ticketswap`.

---

## Step 4 — Install the program

Still in the same terminal window. Paste these one at a time:

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

The last command downloads Chromium (the browser the program drives). It's
about 150 MB; coffee break.

> 💡 Whenever you reopen the terminal later, you have to "activate" the
> environment again with `source .venv/bin/activate` (Mac/Linux) or
> `.venv\Scripts\Activate.ps1` (Windows) before running `python -m
> ticketswap ...` commands. Your prompt shows `(.venv)` when it's active.

---

## Step 5 — Get a Gmail "App Password"

This is the password the program uses to send you alert emails. Don't use
your real Gmail password.

1. Make sure 2-step verification is on for your Google account:
   https://myaccount.google.com/security
2. Open https://myaccount.google.com/apppasswords
3. App: **Mail**. Device: **Other** → type `TicketSwap helper` → Generate.
4. Google shows a 16-character password. Copy it. You'll paste it in the
   next step.

---

## Step 6 — Pick an ntfy topic for phone notifications

ntfy is a free push-notification service. We pick a secret-ish topic name;
your phone subscribes to it; the program posts to it; your phone buzzes.

1. Make up a long random topic name. Example:
   `ticketswap-thomas-9f2k7p3qz4` — your name + random letters/digits.
   **Don't share it.** Anyone who knows it could send you fake
   notifications.
2. On your phone:
   - Install **ntfy** from the App Store / Play Store.
   - Open it → **+ Subscribe to topic**.
   - Topic name: paste the same name you picked.
   - Server: leave as the default (`ntfy.sh`).
3. The full URL you'll need below is `https://ntfy.sh/<your-topic>`.

---

## Step 7 — Set up the program

In the terminal:

```bash
python -m ticketswap setup
```

It asks a series of questions. Press Enter to accept the suggestion in
brackets `[...]`.

| Prompt | What to type |
|---|---|
| SMTP host | press Enter (Gmail) |
| SMTP port | press Enter (587) |
| SMTP user | your Gmail address |
| SMTP password | the **App Password** from Step 5 |
| Alert recipient | the email where you want notifications (usually same as SMTP user) |
| Configure IMAP listener? | `y` (faster reactions) |
| IMAP host / user / password | press Enter / Enter / Enter (uses Gmail values) |
| Configure ntfy push? | `y` |
| Full ntfy URL | `https://ntfy.sh/<your-topic>` from Step 6 |

When it's done, you'll see "Wrote /path/to/.env".

---

## Step 8 — Test that alerts work

```bash
python -m ticketswap test-alerts
```

Within a few seconds you should see:

- A test email in your inbox with a big blue **Open cart** button.
- A notification on your phone (tap it → opens TicketSwap homepage).

If both work, you're set. If something failed, check the error message in
the terminal — usually a typo in the email password or ntfy URL. Re-run
`python -m ticketswap setup` to fix.

---

## Step 9 — Log in to TicketSwap (one time)

```bash
python -m ticketswap login
```

A Chrome window opens. Log in to TicketSwap **as the same account you use
on your phone**. Then go back to the terminal and press Enter.

The window closes. The program saved your login so it doesn't need to ask
again.

> 🔒 The login is saved in a folder called `.chromium-profile` inside the
> project folder. Don't share that folder with anyone — it contains your
> active TicketSwap session.

---

## Step 10 — Add the event you want a ticket for

Get the URL of the event from your browser. For example:

```bash
python -m ticketswap add \
  "https://www.ticketswap.com/concert-tickets/rosalia-antwerp-afas-dome-2026-04-27-CVoAVJWtL6zMBsyXm3fYp" \
  --label "Rosalia Antwerp" \
  --max-price 200 \
  --quantity 1 \
  --mode auto \
  --poll 60
```

What each part means:

- The URL: copy it from your browser. **Keep the quotes around it.**
- `--label`: any name you'll recognise.
- `--max-price`: the most you're willing to pay, in euros. Skip if too
  expensive.
- `--quantity`: how many tickets you want. (For now this is just a note —
  the program reserves whatever listing it finds first.)
- `--mode auto`: try the regular "Buy" button first, fall back to "Join
  raffle" if the event is a raffle. Use `fcfs` if you only want regular
  tickets, `raffle` for raffle-only.
- `--poll 60`: check every 60 seconds.

To check what's saved:

```bash
python -m ticketswap list
```

To remove something:

```bash
python -m ticketswap remove "Rosalia"
```

---

## Step 11 — Start watching

```bash
python -m ticketswap run
```

The terminal will print things like:

```
Loaded 1 active watch(es):
  - Rosalia Antwerp  poll=60s  max=€200.0
IMAP listener started on imap.gmail.com
```

**Leave this window open.** As long as it's running, the program is
checking every minute. If a ticket appears:

1. The program clicks **Add to cart** on the laptop.
2. Your phone gets a ntfy notification with an **Open cart** button.
3. You also get an email with the same button.
4. Tap **Open cart** on your phone. The TicketSwap app opens with the
   ticket already in your basket.
5. Pay (you've already saved a payment method, right?). Done.

You have **about 10 minutes** from the notification before the cart times
out and the ticket goes back to the pool. Don't wait too long.

To stop the program: click in its terminal window and press `Ctrl + C`.

---

## Before you actually need this — pre-flight checks

Do these once, ahead of the event you care about:

- ✅ Run `python -m ticketswap test-alerts`. Email + push both work.
- ✅ On your phone, install the **TicketSwap** app and log in (same
  account the bot uses).
- ✅ In the TicketSwap app, save a **payment method** (card / iDEAL /
  Bancontact). Otherwise checkout takes too long.
- ✅ On your phone, make sure the ntfy app is allowed to show
  notifications when the phone is locked (Settings → Notifications →
  ntfy → Allow).
- ✅ On your laptop, disable sleep / system updates while the bot is
  running (you can re-enable after).

---

## Troubleshooting

**"command not found: python3"**
You skipped Step 2. Install Python.

**"command not found: git"**
Install Git from https://git-scm.com/downloads, then close and reopen
the terminal.

**The browser opens but I get a CAPTCHA**
Solve it manually in the window during `login`. If it happens during a
real claim, the program backs off and waits. There's no way for the
program to bypass CAPTCHAs.

**Email isn't arriving**
Almost always a wrong password. The Gmail App Password (Step 5) is
**not** your normal Gmail password. Re-generate one and re-run
`python -m ticketswap setup`.

**Phone notification isn't arriving**
- Open the ntfy app and check you're subscribed to the right topic.
- Check the URL in your `.env` file matches.
- Check phone notification permissions for the ntfy app.

**The bot says "no buy button visible" but a ticket is clearly there**
Means the locator missed. Look at the most recent screenshot in the
`shots/` folder. The website's HTML may have changed slightly. Open a
GitHub issue with the screenshot and we'll update.

**Account got banned**
Sorry. Read the warning at the top of this README again before trying
to make a new one.

---

## What this program does NOT do

- It does **not** pay for the ticket. You always do that step.
- It does **not** work for raffle events any faster than a human (raffles
  pick winners randomly; speed doesn't help).
- It does **not** bypass CAPTCHAs or other anti-bot challenges.
- It does **not** run in the cloud. Your computer has to be on.

---

## Files in this repo

- `PLAN.md` — design doc with risks and tradeoffs (technical).
- `CLAUDE.md` — notes for Claude when extending the code.
- `ticketswap/` — the program's source code.
- `tests/` — automated tests for parts of the code.

If anything in this guide is unclear, open a GitHub issue.
