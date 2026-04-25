from ticketswap.poller import looks_available


def test_looks_available_buy_path():
    assert looks_available('<a href="/event/foo/buy/123">Buy</a>')


def test_looks_available_text_hint():
    assert looks_available("<button>Add to cart</button>")


def test_looks_available_dutch():
    assert looks_available("<a>Koop ticket</a>")


def test_not_available_when_sold_out():
    html = "<html><body><p>No tickets available right now.</p></body></html>"
    assert not looks_available(html)
