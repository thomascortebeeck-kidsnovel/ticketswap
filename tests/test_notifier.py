from ticketswap.notifier import build_messages


CART = "https://www.ticketswap.com/cart/abc123"
LISTING = "https://www.ticketswap.com/event/x-AbCdEfGhIjKlMnOpQrStU"


def test_reservation_subject_signals_urgency():
    subject, _, _, _ = build_messages(
        label="Rosalia Antwerp",
        cart_url=CART,
        listing_url=LISTING,
        kind="reservation",
        message="Reserved",
    )
    assert subject.startswith("[RESERVED]")
    assert "Rosalia Antwerp" in subject
    assert "PAY NOW" in subject  # so the lock-screen preview is unmissable


def test_raffle_subject_says_raffle_not_pay():
    subject, text, _, _ = build_messages(
        label="Rosalia Antwerp",
        cart_url=CART,
        listing_url=LISTING,
        kind="raffle",
        message="Entered raffle",
    )
    assert subject.startswith("[RAFFLE ENTERED]")
    assert "PAY NOW" not in subject
    assert "raffle" in text.lower()


def test_plain_text_has_cart_url_on_first_body_line():
    """So mobile mail clients render it as a tappable link without scrolling."""
    _, text, _, _ = build_messages(
        label="x", cart_url=CART, listing_url=LISTING, kind="reservation", message="ok"
    )
    lines = text.splitlines()
    # First non-empty line is the action; second is "Open: <url>".
    assert any(CART in line for line in lines[:4])


def test_html_body_has_button_pointing_to_cart():
    _, _, html_body, _ = build_messages(
        label="x", cart_url=CART, listing_url=LISTING, kind="reservation", message="ok"
    )
    assert f'href="{CART}"' in html_body
    assert "Open cart" in html_body


def test_whatsapp_message_is_short_and_has_url():
    _, _, _, wa = build_messages(
        label="Rosalia Antwerp",
        cart_url=CART,
        listing_url=LISTING,
        kind="reservation",
        message="ok",
    )
    assert CART in wa
    assert "Rosalia Antwerp" in wa
    assert "RESERVED" in wa.upper()
    assert len(wa) < 300  # CallMeBot prefers short messages


def test_html_body_escapes_label():
    _, _, html_body, _ = build_messages(
        label="<script>alert(1)</script>",
        cart_url=CART,
        listing_url=LISTING,
        kind="reservation",
        message="ok",
    )
    assert "<script>" not in html_body
    assert "&lt;script&gt;" in html_body
