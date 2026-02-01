from ccxt.base.types import Entry


class ImplicitAPI:
    # Public endpoints (REST style)
    public_get_get_instruments = publicGetGetInstruments = Entry('get_instruments', 'public', 'GET', {'cost': 1})
    public_get_get_order_book = publicGetGetOrderBook = Entry('get_order_book', 'public', 'GET', {'cost': 1})
    public_get_tickers = publicGetTickers = Entry('tickers', 'public', 'GET', {'cost': 1})

    # Public auth (placeholder for future use)
    public_post_auth = publicPostAuth = Entry('auth', 'public', 'POST', {'cost': 1})

    # Private endpoints (placeholder for future use)
    private_post_logout = privatePostLogout = Entry('logout', 'private', 'POST', {'cost': 1})
