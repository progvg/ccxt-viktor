# -*- coding: utf-8 -*-

# CCXT Pro WebSocket support for OrangeX (JSON-RPC over WebSocket)

import ccxt.async_support
from ccxt.async_support.base.ws.cache import ArrayCacheBySymbolById
from ccxt.async_support.base.ws.client import Client
from ccxt.base.types import Any, Int, OrderBook, Str, Ticker
from ccxt.base.errors import AuthenticationError, ArgumentsRequired, ExchangeError


class orangex(ccxt.async_support.orangex):

    def describe(self) -> Any:
        return self.deep_extend(super(orangex, self).describe(), {
            'has': {
                'ws': True,
                'watchTicker': True,
                'watchTickers': False,
                'watchOrderBook': True,
                'watchOrders': False,
                'watchTrades': False,
                'watchBalance': False,
                'watchOHLCV': False,
            },
            'urls': {
                'api': {
                    'ws': 'wss://api.orangex.com/ws/api/v1',
                },
            },
            'options': {
                'watchTicker': {
                    'interval': 'raw',
                },
                'watchOrderBook': {
                    'interval': 'raw',
                },
                'ordersLimit': 1000,
            },
        })

    async def authenticate(self, params={}):
        url = self.urls['api']['ws']
        client = self.client(url)
        messageHash = 'authenticated'
        future = self.safe_value(client.subscriptions, messageHash)
        expires = self.safe_integer(self.options, 'expires')
        token = self.safe_string(self.options, 'accessToken')
        if future is None or token is None or ((expires is not None) and (expires < self.milliseconds())):
            self.check_required_credentials()
            request = {
                'jsonrpc': '2.0',
                'id': self.nonce(),
                'method': '/public/auth',
                'params': {
                    'grant_type': 'client_credentials',
                    'client_id': self.apiKey,
                    'client_secret': self.secret,
                },
            }
            future = await self.watch(url, messageHash, self.deep_extend(request, params), messageHash)
            client.subscriptions[messageHash] = future
        return future

    async def subscribe(self, channel, messageHash, isPrivate=False, params={}):
        url = self.urls['api']['ws']
        request: dict = {
            'jsonrpc': '2.0',
            'id': self.nonce(),
            'method': '/private/subscribe' if isPrivate else '/public/subscribe',
            'params': {
                'channels': [channel],
            },
        }
        if isPrivate:
            await self.authenticate(params)
            token = self.safe_string(self.options, 'accessToken')
            if token is None:
                raise AuthenticationError(self.id + ' missing access token in options["accessToken"]')
            request['params']['access_token'] = token
        return await self.watch(url, messageHash, self.deep_extend(request, params), messageHash)

    def resolve_market(self, marketId):
        if marketId is None:
            return None
        if marketId in self.markets_by_id:
            return self.safe_market(marketId)
        if not marketId.endswith('-SPOT'):
            spotId = marketId + '-SPOT'
            if spotId in self.markets_by_id:
                return self.safe_market(spotId)
        return self.safe_market(marketId)

    async def watch_ticker(self, symbol: str, params={}) -> Ticker:
        await self.load_markets()
        market = self.market(symbol)
        interval = self.safe_string(params, 'interval')
        if interval is None:
            interval = self.safe_string(self.options.get('watchTicker', {}), 'interval', 'raw')
        params = self.omit(params, 'interval')
        channel = 'ticker.' + market['id'] + '.' + interval
        messageHash = channel
        return await self.subscribe(channel, messageHash, False, params)

    async def watch_order_book(self, symbol: str, limit: Int = None, params={}) -> OrderBook:
        await self.load_markets()
        market = self.market(symbol)
        interval = self.safe_string(params, 'interval')
        if interval is None:
            interval = self.safe_string(self.options.get('watchOrderBook', {}), 'interval', 'raw')
        params = self.omit(params, 'interval')
        channel = 'book.' + market['id'] + '.' + interval
        messageHash = channel
        orderbook = await self.subscribe(channel, messageHash, False, params)
        if limit is not None:
            orderbook = orderbook.limit()
        return orderbook

    async def watch_orders(self, symbol: Str = None, since: Int = None, limit: Int = None, params={}):
        await self.load_markets()
        if symbol is None:
            raise ArgumentsRequired(self.id + ' watchOrders() requires a symbol')
        market = self.market(symbol)
        channel = 'user.orders.' + market['id'] + '.raw'
        messageHash = 'orders:' + market['symbol']
        orders = await self.subscribe(channel, messageHash, True, params)
        if self.newUpdates:
            limit = orders.getLimit(symbol, limit)
        return self.filter_by_symbol_since_limit(orders, market['symbol'], since, limit, True)

    def handle_ticker(self, client: Client, message):
        params = self.safe_dict(message, 'params', {})
        data = self.safe_dict(params, 'data', {})
        channel = self.safe_string(params, 'channel')
        marketId = self.safe_string(data, 'instrument_name')
        market = self.resolve_market(marketId)
        ticker = self.parse_ticker(data, market)
        symbol = ticker['symbol']
        self.tickers[symbol] = ticker
        if channel is not None:
            client.resolve(ticker, channel)
        client.resolve(ticker, 'ticker:' + symbol)

    def handle_order_book(self, client: Client, message):
        params = self.safe_dict(message, 'params', {})
        data = self.safe_dict(params, 'data', {})
        channel = self.safe_string(params, 'channel')
        marketId = self.safe_string(data, 'instrument_name')
        market = self.resolve_market(marketId)
        symbol = market['symbol'] if market is not None else None
        if symbol is None:
            return
        orderbook = self.safe_value(self.orderbooks, symbol)
        if orderbook is None:
            orderbook = self.order_book()
            self.orderbooks[symbol] = orderbook
        timestamp = self.safe_integer(data, 'timestamp')
        changeId = self.safe_integer(data, 'change_id')
        orderbook['timestamp'] = timestamp
        orderbook['datetime'] = self.iso8601(timestamp)
        orderbook['nonce'] = changeId
        for side in ['bids', 'asks']:
            updates = self.safe_list(data, side, [])
            bookSide = orderbook[side]
            for i in range(0, len(updates)):
                update = updates[i]
                action = None
                price = None
                amount = None
                if isinstance(update, list):
                    if len(update) >= 3 and isinstance(update[0], str):
                        action = self.safe_string(update, 0)
                        price = self.safe_number(update, 1)
                        amount = self.safe_number(update, 2)
                    else:
                        price = self.safe_number(update, 0)
                        amount = self.safe_number(update, 1)
                elif isinstance(update, dict):
                    action = self.safe_string(update, 'action')
                    price = self.safe_number(update, 'price')
                    amount = self.safe_number(update, 'amount')
                if action == 'delete':
                    amount = 0
                if price is None:
                    continue
                bookSide.storeArray([price, amount])
        if channel is not None:
            client.resolve(orderbook, channel)
        client.resolve(orderbook, 'orderbook:' + symbol)

    def handle_orders(self, client: Client, message):
        params = self.safe_dict(message, 'params', {})
        data = self.safe_value(params, 'data')
        channel = self.safe_string(params, 'channel')
        orders = data if isinstance(data, list) else [data]
        stored = self.orders
        if stored is None:
            limit = self.safe_integer(self.options, 'ordersLimit', 1000)
            stored = ArrayCacheBySymbolById(limit)
            self.orders = stored
        for order in orders:
            if order is None:
                continue
            parsed = self.parse_order(order)
            symbol = parsed['symbol']
            if symbol is None and channel is not None:
                parts = channel.split('.')
                if len(parts) > 2:
                    market = self.resolve_market(parts[2])
                    if market is not None:
                        symbol = market['symbol']
                        parsed['symbol'] = symbol
            stored.append(parsed)
            client.resolve(stored, 'orders')
            if symbol is not None:
                client.resolve(stored, 'orders:' + symbol)

    def handle_message(self, client: Client, message):
        error = self.safe_value(message, 'error')
        if error is not None:
            code = self.safe_string(error, 'code')
            msg = self.safe_string(error, 'message')
            raise ExchangeError(self.id + ' ' + self.json({'code': code, 'message': msg}))
        method = self.safe_string(message, 'method')
        if method != 'subscription':
            result = self.safe_value(message, 'result', {})
            access_token = self.safe_string(result, 'access_token')
            if access_token is not None:
                self.options['accessToken'] = access_token
                expires_in = self.safe_integer(result, 'expires_in')
                if expires_in is not None:
                    self.options['expires'] = self.sum(self.milliseconds(), expires_in * 1000)
                client.resolve(message, 'authenticated')
            return
        params = self.safe_dict(message, 'params', {})
        channel = self.safe_string(params, 'channel')
        if channel is None:
            return
        if channel.startswith('ticker.'):
            return self.handle_ticker(client, message)
        if channel.startswith('book.'):
            return self.handle_order_book(client, message)
        if channel.startswith('user.orders.'):
            return self.handle_orders(client, message)
