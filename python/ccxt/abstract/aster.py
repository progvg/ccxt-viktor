from ccxt.base.types import Entry


class ImplicitAPI:
    # Public endpoints
    public_get_ping = publicGetPing = Entry('ping', 'public', 'GET', {'cost': 1})
    public_get_time = publicGetTime = Entry('time', 'public', 'GET', {'cost': 1})
    public_get_exchangeinfo = publicGetExchangeInfo = Entry('exchangeInfo', 'public', 'GET', {'cost': 10})
    public_get_depth = publicGetDepth = Entry('depth', 'public', 'GET', {'cost': 1, 'byLimit': [[100, 1], [500, 5], [1000, 10], [5000, 50]]})
    public_get_trades = publicGetTrades = Entry('trades', 'public', 'GET', {'cost': 1})
    public_get_historicaltrades = publicGetHistoricalTrades = Entry('historicalTrades', 'public', 'GET', {'cost': 5})
    public_get_aggtrades = publicGetAggTrades = Entry('aggTrades', 'public', 'GET', {'cost': 1})
    public_get_klines = publicGetKlines = Entry('klines', 'public', 'GET', {'cost': 1})
    public_get_ticker_24hr = publicGetTicker24hr = Entry('ticker/24hr', 'public', 'GET', {'cost': 1, 'noSymbol': 40})
    public_get_ticker_price = publicGetTickerPrice = Entry('ticker/price', 'public', 'GET', {'cost': 1, 'noSymbol': 2})
    public_get_ticker_bookticker = publicGetTickerBookTicker = Entry('ticker/bookTicker', 'public', 'GET', {'cost': 1, 'noSymbol': 2})
    public_get_commissionrate = publicGetCommissionRate = Entry('commissionRate', 'public', 'GET', {'cost': 1})

    # Private (signed) endpoints
    private_get_account = privateGetAccount = Entry('account', 'private', 'GET', {'cost': 10})
    private_get_order = privateGetOrder = Entry('order', 'private', 'GET', {'cost': 2})
    private_get_openorders = privateGetOpenOrders = Entry('openOrders', 'private', 'GET', {'cost': 3, 'noSymbol': 40})
    private_get_allorders = privateGetAllOrders = Entry('allOrders', 'private', 'GET', {'cost': 10})
    private_get_usertrades = privateGetUserTrades = Entry('userTrades', 'private', 'GET', {'cost': 10})

    private_post_order = privatePostOrder = Entry('order', 'private', 'POST', {'cost': 1})
    private_delete_order = privateDeleteOrder = Entry('order', 'private', 'DELETE', {'cost': 1})
    private_delete_allopenorders = privateDeleteAllOpenOrders = Entry('allOpenOrders', 'private', 'DELETE', {'cost': 1})

    # Additional asset/withdrawal endpoints as per spec (optional usage)
    private_post_asset_wallet_transfer = privatePostAssetWalletTransfer = Entry('asset/wallet/transfer', 'private', 'POST', {'cost': 1})
    private_post_asset_sendtoaddress = privatePostAssetSendToAddress = Entry('asset/sendToAddress', 'private', 'POST', {'cost': 1})
    public_get_aster_withdraw_estimatefee = publicGetAsterWithdrawEstimateFee = Entry('aster/withdraw/estimateFee', 'public', 'GET', {'cost': 1})
    private_post_aster_user_withdraw = privatePostAsterUserWithdraw = Entry('aster/user-withdraw', 'private', 'POST', {'cost': 1})

    # Listen key management (USER_STREAM)
    public_post_listenkey = publicPostListenKey = Entry('listenKey', 'public', 'POST', {'cost': 1})
    public_put_listenkey = publicPutListenKey = Entry('listenKey', 'public', 'PUT', {'cost': 1})
    public_delete_listenkey = publicDeleteListenKey = Entry('listenKey', 'public', 'DELETE', {'cost': 1})


    # alias to match binance ws helper expectations
    public_post_userdatastream = publicPostUserDataStream = Entry('listenKey', 'public', 'POST', {'cost': 1})
    public_put_userdatastream = publicPutUserDataStream = Entry('listenKey', 'public', 'PUT', {'cost': 1})
    public_delete_userdatastream = publicDeleteUserDataStream = Entry('listenKey', 'public', 'DELETE', {'cost': 1})

    # SAPI aliases (header-only auth like Binance)
    sapi_post_userdatastream = sapiPostUserDataStream = Entry('listenKey', 'sapi', 'POST', {'cost': 1})
    sapi_put_userdatastream = sapiPutUserDataStream = Entry('listenKey', 'sapi', 'PUT', {'cost': 1})
    sapi_delete_userdatastream = sapiDeleteUserDataStream = Entry('listenKey', 'sapi', 'DELETE', {'cost': 1})

