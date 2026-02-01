from ccxt.base.types import Entry


class ImplicitAPI:
    # Public endpoints (REST style)
    public_get_get_instruments = publicGetGetInstruments = Entry('get_instruments', 'public', 'GET', {'cost': 1})
    public_get_get_order_book = publicGetGetOrderBook = Entry('get_order_book', 'public', 'GET', {'cost': 1})
    public_get_tickers = publicGetTickers = Entry('tickers', 'public', 'GET', {'cost': 1})

    # Public auth
    public_post_auth = publicPostAuth = Entry('auth', 'public', 'POST', {'cost': 1})

    # Private endpoints
    private_post_logout = privatePostLogout = Entry('logout', 'private', 'POST', {'cost': 1})
    private_post_buy = privatePostBuy = Entry('buy', 'private', 'POST', {'cost': 1})
    private_post_sell = privatePostSell = Entry('sell', 'private', 'POST', {'cost': 1})
    private_post_cancel = privatePostCancel = Entry('cancel', 'private', 'POST', {'cost': 1})
    private_post_cancel_all_by_currency = privatePostCancelAllByCurrency = Entry('cancel_all_by_currency', 'private', 'POST', {'cost': 1})
    private_post_cancel_all_by_instrument = privatePostCancelAllByInstrument = Entry('cancel_all_by_instrument', 'private', 'POST', {'cost': 1})
    private_post_get_open_orders_by_currency = privatePostGetOpenOrdersByCurrency = Entry('get_open_orders_by_currency', 'private', 'POST', {'cost': 1})
    private_post_get_open_orders_by_instrument = privatePostGetOpenOrdersByInstrument = Entry('get_open_orders_by_instrument', 'private', 'POST', {'cost': 1})
    private_post_get_order_history_by_currency = privatePostGetOrderHistoryByCurrency = Entry('get_order_history_by_currency', 'private', 'POST', {'cost': 1})
    private_post_get_order_history_by_instrument = privatePostGetOrderHistoryByInstrument = Entry('get_order_history_by_instrument', 'private', 'POST', {'cost': 1})
    private_post_get_order_state = privatePostGetOrderState = Entry('get_order_state', 'private', 'POST', {'cost': 1})
    private_post_get_user_trades_by_currency = privatePostGetUserTradesByCurrency = Entry('get_user_trades_by_currency', 'private', 'POST', {'cost': 1})
    private_post_get_user_trades_by_instrument = privatePostGetUserTradesByInstrument = Entry('get_user_trades_by_instrument', 'private', 'POST', {'cost': 1})
    private_post_get_user_trades_by_order = privatePostGetUserTradesByOrder = Entry('get_user_trades_by_order', 'private', 'POST', {'cost': 1})
    private_post_get_positions = privatePostGetPositions = Entry('get_positions', 'private', 'POST', {'cost': 1})
    private_post_close_position = privatePostClosePosition = Entry('close_position', 'private', 'POST', {'cost': 1})
    private_post_get_assets_info = privatePostGetAssetsInfo = Entry('get_assets_info', 'private', 'POST', {'cost': 1})
