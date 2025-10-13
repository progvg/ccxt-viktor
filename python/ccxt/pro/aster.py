# -*- coding: utf-8 -*-

# CCXT Pro WebSocket support for Aster (Binance-like streaming API)

from ccxt.pro.binance import binance
from ccxt.base.types import Any
from ccxt.base.exchange import Exchange

import ccxt.async_support.aster as asterRest


class aster(binance):

    def describe(self) -> Any:
        # merge REST describe and WS describe from parent
        restInstance = asterRest()
        restDescribe = restInstance.describe()
        parentWsDescribe = super(aster, self).describe_data()
        extended = self.deep_extend(restDescribe, parentWsDescribe)
        return self.deep_extend(extended, {
            'id': 'aster',
            'name': 'Aster',
            'pro': True,
            'urls': {
                'api': {
                    'ws': {
                        'spot': 'wss://sstream.asterdex.com/ws',
                        'ws-api': {
                            'spot': None,
                        },
                    },
                },
                'doc': 'https://sapi.asterdex.com',
            },
        })

    # Normalize high-precision timestamps (µs/ns) to milliseconds
    def iso8601(self, timestamp=None):
        if timestamp is None:
            return timestamp
        # delegate non-int (e.g. str) to base static helper
        if not isinstance(timestamp, int):
            return Exchange.iso8601(timestamp)
        ts = int(timestamp)
        if ts > 100000000000000000:  # ns
            ts //= 1000000
        elif ts > 100000000000000:   # µs
            ts //= 1000
        elif ts < 100000000000:      # s
            ts *= 1000
        return Exchange.iso8601(ts)

    async def authenticate(self, params={}):
        # Use REST aster client to obtain listenKey reliably
        time = self.milliseconds()
        mtype = None
        mtype, params = self.handle_market_type_and_params('authenticate', None, params)
        if mtype is None:
            mtype = 'spot'
        options = self.safe_value(self.options, mtype, {})
        lastAuthenticatedTime = self.safe_integer(options, 'lastAuthenticatedTime', 0)
        listenKeyRefreshRate = self.safe_integer(self.options, 'listenKeyRefreshRate', 1200000)
        delay = self.sum(listenKeyRefreshRate, 10000)
        listenKey = self.safe_string(options, 'listenKey')
        if (listenKey is None) or ((time - lastAuthenticatedTime) > delay):
            # instantiate REST aster to call POST /api/v1/listenKey
            rest = asterRest({
                'apiKey': self.apiKey,
                'secret': self.secret,
                'timeout': self.timeout,
                'options': {
                    'recvWindow': self.safe_integer_2(self.options, 'recvWindow', 'spot', 5000),
                },
            })
            try:
                response = await rest.publicPostUserDataStream(params)
            finally:
                try:
                    await rest.close()
                except Exception:
                    pass
            listenKey = self.safe_string(response, 'listenKey')
            self.options[mtype] = self.extend(options, {
                'listenKey': listenKey,
                'lastAuthenticatedTime': time,
            })
            self.delay(listenKeyRefreshRate, self.keep_alive_listen_key, params)
        return listenKey

    async def watch_orders(self, symbol: str = None, since: int = None, limit: int = None, params={}):
        await self.load_markets()
        messageHash = 'orders'
        market = None
        if symbol is not None:
            market = self.market(symbol)
            symbol = market['symbol']
            messageHash += ':' + symbol
        params = self.extend(params, {'type': 'spot', 'symbol': symbol})
        await self.authenticate(params)
        url = self.urls['api']['ws']['spot'] + '/' + self.options['spot']['listenKey']
        client = self.client(url)
        self.set_balance_cache(client, 'spot', None)
        self.set_positions_cache(client, 'spot', None, None)
        message = None
        orders = await self.watch(url, messageHash, message, 'spot')
        if self.newUpdates:
            ordersLimit = orders.getLimit(symbol, limit)
            limit = ordersLimit
        return self.filter_by_symbol_since_limit(orders, symbol, since, limit, True)

    def handle_message(self, client, message):
        # Normalize potential Aster-specific event names to Binance semantics
        event = self.safe_string(message, 'e')
        if event is None and isinstance(message, dict):
            if ('i' in message) and (('X' in message) or ('x' in message)) and (('s' in message) or ('symbol' in message)):
                self.handle_order_update(client, message)
                return
        if event in ('order', 'ORDER', 'orderUpdate'):
            message['e'] = 'executionReport'
        return super(aster, self).handle_message(client, message)

