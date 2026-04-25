from __future__ import annotations

import httpx


def send_push(
    ntfy_url: str,
    title: str,
    body: str,
    click_url: str | None = None,
    priority: str = "high",
    tags: str = "ticket",
) -> None:
    """POST a push notification to an ntfy.sh topic.

    `ntfy_url` is the full topic URL, e.g. https://ntfy.sh/my-secret-topic.
    Subscribe to the same URL in the ntfy app on your phone and you'll get
    an instant notification with an "Open cart" tap action.
    """
    headers = {
        "Title": title,
        "Priority": priority,
        "Tags": tags,
    }
    if click_url:
        # Tapping the notification body opens this URL.
        headers["Click"] = click_url
        # Also add an explicit "Open cart" button in the notification.
        headers["Actions"] = f"view, Open cart, {click_url}, clear=true"
    r = httpx.post(
        ntfy_url,
        content=body.encode("utf-8"),
        headers=headers,
        timeout=10,
    )
    r.raise_for_status()
