# -*- coding: utf-8 -*-

from ccxt.async_support.base.exchange import Exchange
from ccxt.abstract.orangex import ImplicitAPI
from ccxt.base.types import Any
from ccxt.base.errors import AuthenticationError, ExchangeError
from ccxt.base.exchange import Exchange as SyncExchange
from ccxt.base.decimal_to_precision import DECIMAL_PLACES


class orangex(ImplicitAPI, Exchange):

    def describe(self) -> Any:
        parent = super(orangex, self).describe()
        return self.deep_extend(parent, {
            'id': 'orangex',
            'name': 'OrangeX',
            'countries': [],
            'certified': False,
            'pro': False,
            'version': 'v1',
            'rateLimit': 100,
            'has': self.deep_extend(parent.get('has', {}), {
                'spot': True,
                'margin': False,
                'swap': True,
                'future': False,
                'option': False,
                'fetchMarkets': True,
                'fetchOrderBook': True,
                'fetchTicker': True,
                'fetchTickers': True,
                'fetchTime': True,
                'fetchBalance': True,
                'createOrder': True,
                'cancelOrder': True,
                'cancelAllOrders': True,
                'fetchOrder': True,
                'fetchOpenOrders': True,
                'fetchOrders': True,
                'fetchClosedOrders': True,
                'fetchMyTrades': True,
                'fetchPositions': True,
                'closePosition': True,
                'fetchTrades': False,
                'fetchOHLCV': False,
            }),
            'urls': {
                'logo': None,
                'api': {
                    'public': 'https://api.orangex.com/api/v1',
                    'private': 'https://api.orangex.com/api/v1',
                },
                'www': 'https://www.orangex.com',
                'doc': 'https://openapi-docs.orangex.com',
            },
            'precisionMode': DECIMAL_PLACES,
            'options': self.deep_extend(parent.get('options', {}), {
                'defaultType': 'spot',
                'fetchMarkets': {
                    'types': ['spot', 'swap'],
                },
                'timeInForce': {
                    'GTC': 'good_til_cancelled',
                    'IOC': 'immediate_or_cancel',
                    'FOK': 'fill_or_kill',
                },
                'accessToken': None,
                'refreshToken': None,
                'expires': None,
            }),
        })

    # Normalize high-precision timestamps (us/ns) to milliseconds
    def iso8601(self, timestamp=None):
        if timestamp is None:
            return timestamp
        if not isinstance(timestamp, int):
            return SyncExchange.iso8601(timestamp)
        ts = self._normalize_timestamp(timestamp)
        return SyncExchange.iso8601(ts)

    def _normalize_timestamp(self, timestamp):
        if timestamp is None:
            return None
        try:
            ts = int(timestamp)
        except Exception:
            return None
        if ts > 100000000000000000:  # ns
            ts //= 1000000
        elif ts > 100000000000000:   # us
            ts //= 1000
        elif ts < 100000000000:      # seconds
            ts *= 1000
        return ts

    def nonce(self):
        return self.milliseconds()

    async def fetch_time(self, params={}):
        response = await self.public_get_get_instruments(self.extend({'currency': 'SPOT'}, params))
        timestamp = self.safe_integer_2(response, 'usOut', 'usIn')
        return self._normalize_timestamp(timestamp)

    async def fetch_markets(self, params={}):
        market_type, params = self.handle_market_type_and_params('fetchMarkets', None, params)
        if market_type is None:
            market_type = self.safe_string(self.options, 'defaultType', 'spot')
        request = {}
        if market_type == 'spot':
            request['currency'] = 'SPOT'
        elif market_type == 'swap':
            request['currency'] = 'PERPETUAL'
        else:
            currency = self.safe_string(params, 'currency')
            if currency is None:
                currency = 'PERPETUAL'
            request['currency'] = currency
        params = self.omit(params, ['type', 'currency'])
        response = await self.public_get_get_instruments(self.extend(request, params))
        result = self.safe_list(response, 'result', [])
        markets = []
        for market in result:
            kind = self.safe_string(market, 'kind')
            if (market_type == 'spot') and (kind != 'spot'):
                continue
            if (market_type == 'swap') and (kind != 'perpetual'):
                continue
            if (market_type == 'future') and (kind != 'future'):
                continue
            markets.append(self.parse_market(market))
        return markets

    def parse_market(self, market):
        market_id = self.safe_string(market, 'instrument_name')
        kind = self.safe_string(market, 'kind')
        is_perpetual = kind == 'perpetual'
        is_future = kind == 'future'
        spot = kind == 'spot' or kind == 'margin'
        contract = is_perpetual or is_future
        base_id = None
        quote_id = None
        show_name = self.safe_string(market, 'show_name')
        if (show_name is not None) and ('/' in show_name):
            parts = show_name.split('/')
            if len(parts) >= 2:
                base_id = parts[0]
                quote_id = parts[1]
        elif market_id is not None:
            parts = market_id.split('-')
            if len(parts) >= 2:
                base_id = parts[0]
                quote_id = parts[1]
        base = self.safe_currency_code(base_id)
        quote = self.safe_currency_code(quote_id)
        settle_id = self.safe_string(market, 'base_currency')
        settle = self.safe_currency_code(settle_id)
        symbol = None
        if (base is not None) and (quote is not None):
            symbol = base + '/' + quote
            if contract and (settle is not None):
                symbol += ':' + settle
        elif market_id is not None:
            symbol = market_id
        linear = None
        inverse = None
        if contract and (settle is not None):
            if settle == quote:
                linear = True
                inverse = False
            elif settle == base:
                linear = False
                inverse = True
        amount_prec = self.safe_integer(market, 'quantityPrec')
        precision = {
            'price': self.precision_from_string(self.safe_string(market, 'tick_size')),
            'amount': amount_prec if amount_prec is not None else self.precision_from_string(self.safe_string(market, 'min_trade_amount')),
        }
        limits = {
            'amount': {
                'min': self.safe_number_2(market, 'min_qty', 'min_trade_amount'),
                'max': None,
            },
            'price': {
                'min': None,
                'max': None,
            },
            'cost': {
                'min': self.safe_number(market, 'min_notional'),
                'max': None,
            },
        }
        active = self.safe_bool(market, 'is_active', True)
        return {
            'id': market_id,
            'symbol': symbol,
            'base': base,
            'quote': quote,
            'settle': settle if contract else None,
            'baseId': base_id,
            'quoteId': quote_id,
            'settleId': settle_id if contract else None,
            'type': 'swap' if is_perpetual else ('future' if is_future else ('spot' if spot else kind)),
            'spot': spot,
            'margin': kind == 'margin',
            'swap': is_perpetual,
            'future': is_future,
            'option': False,
            'active': active,
            'contract': contract,
            'linear': linear,
            'inverse': inverse,
            'contractSize': None,
            'expiry': None,
            'expiryDatetime': None,
            'strike': None,
            'optionType': None,
            'taker': self.safe_number(market, 'taker_commission'),
            'maker': self.safe_number(market, 'maker_commission'),
            'precision': precision,
            'limits': limits,
            'info': market,
        }

    async def fetch_order_book(self, symbol: str, limit=None, params={}):
        await self.load_markets()
        market = self.market(symbol)
        request = {
            'instrument_name': market['id'],
        }
        if limit is not None:
            request['depth'] = limit
        response = await self.public_get_get_order_book(self.extend(request, params))
        result = self.safe_value(response, 'result', {})
        timestamp = self._normalize_timestamp(self.safe_integer(result, 'timestamp'))
        return self.parse_order_book(result, symbol, timestamp, 'bids', 'asks')

    async def fetch_ticker(self, symbol: str, params={}):
        await self.load_markets()
        market = self.market(symbol)
        request = {
            'instrument_name': market['id'],
        }
        response = await self.public_get_tickers(self.extend(request, params))
        result = self.safe_value(response, 'result', [])
        ticker = result[0] if isinstance(result, list) and (len(result) > 0) else result
        return self.parse_ticker(ticker, market)

    async def fetch_tickers(self, symbols=None, params={}):
        await self.load_markets()
        symbols = self.market_symbols(symbols)
        market_type, params = self.handle_market_type_and_params('fetchTickers', None, params)
        params = self.omit(params, 'currency')
        types = []
        if symbols is not None:
            if market_type is None:
                for symbol in symbols:
                    market = self.market(symbol)
                    types.append('swap' if market['swap'] else 'spot')
                types = list(set(types))
            else:
                types = [market_type]
        else:
            if market_type is None:
                market_type = self.safe_string(self.options, 'defaultType', 'spot')
            types = [market_type]
        tickers = []
        for t in types:
            currency = 'PERPETUAL' if t in ['swap', 'perpetual'] else 'SPOT'
            response = await self.public_get_tickers(self.extend({'currency': currency}, params))
            data = self.safe_list(response, 'result', [])
            for entry in data:
                market_id = self.safe_string(entry, 'instrument_name')
                market = None
                if market_id is not None:
                    lookup_id = market_id
                    if currency == 'SPOT' and not market_id.endswith('-SPOT'):
                        lookup_id = market_id + '-SPOT'
                    market = self.safe_market(lookup_id, None, None, 'spot' if currency == 'SPOT' else 'swap')
                tickers.append(self.parse_ticker(entry, market))
        return self.filter_by_array_tickers(tickers, 'symbol', symbols)

    def parse_ticker(self, ticker, market=None):
        timestamp = self._normalize_timestamp(self.safe_integer(ticker, 'timestamp'))
        stats = self.safe_value(ticker, 'stats', {})
        symbol = market['symbol'] if market is not None else None
        high = self.safe_number(stats, 'high')
        if high is None:
            high = self.safe_number(ticker, 'high')
        low = self.safe_number(stats, 'low')
        if low is None:
            low = self.safe_number(ticker, 'low')
        return self.safe_ticker({
            'symbol': symbol,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'high': high,
            'low': low,
            'bid': self.safe_number_2(ticker, 'best_bid_price', 'bid'),
            'ask': self.safe_number_2(ticker, 'best_ask_price', 'ask'),
            'last': self.safe_number_2(ticker, 'last_price', 'last'),
            'baseVolume': self.safe_number(stats, 'volume'),
            'quoteVolume': self.safe_number_2(stats, 'turnover', 'volume_usd'),
            'percentage': self.safe_number(stats, 'price_change'),
            'info': ticker,
        }, market)

    async def sign_in(self, params={}):
        """
        sign in, must be called prior to using other authenticated methods
        """
        self.check_required_credentials()
        request = {
            'grant_type': 'client_credentials',
            'client_id': self.apiKey,
            'client_secret': self.secret,
        }
        rpc_request = {
            'jsonrpc': '2.0',
            'id': self.nonce(),
            'method': '/public/auth',
            'params': self.extend(request, params),
        }
        response = await self.public_post_auth(rpc_request)
        result = self.safe_value(response, 'result', {})
        access_token = self.safe_string(result, 'access_token')
        if access_token is None:
            raise AuthenticationError(self.id + ' signIn failed')
        self.options['accessToken'] = access_token
        self.options['refreshToken'] = self.safe_string(result, 'refresh_token')
        expires_in = self.safe_integer(result, 'expires_in')
        if expires_in is not None:
            self.options['expires'] = self.sum(self.milliseconds(), expires_in * 1000)
        return response

    async def fetch_balance(self, params={}):
        await self.load_markets()
        market_type, params = self.handle_market_type_and_params('fetchBalance', None, params)
        asset_type = self.safe_string(params, 'asset_type')
        if asset_type is None:
            if market_type is None:
                market_type = self.safe_string(self.options, 'defaultType', 'spot')
            if market_type in ['spot']:
                asset_type = 'SPOT'
            elif market_type in ['swap', 'perpetual']:
                asset_type = 'PERPETUAL'
            elif market_type in ['wallet']:
                asset_type = 'WALLET'
            else:
                asset_type = 'ALL'
        params = self.omit(params, ['type', 'asset_type'])
        request = {
            'asset_type': asset_type if isinstance(asset_type, list) else [asset_type],
        }
        response = await self.private_post_get_assets_info(self.extend(request, params))
        result = self.safe_value(response, 'result', {})
        section = self.safe_value(result, asset_type, {})
        if asset_type == 'ALL':
            section = result
        balance = {
            'info': response,
        }
        details = self.safe_list(section, 'details', [])
        for entry in details:
            currency_id = self.safe_string(entry, 'coin_type')
            code = self.safe_currency_code(currency_id)
            if code is None:
                continue
            free = self.safe_number(entry, 'available')
            used = self.safe_number(entry, 'freeze')
            total = self.safe_number(entry, 'total')
            if total is None:
                total = self.sum(free, used)
            balance[code] = {
                'free': free,
                'used': used,
                'total': total,
            }
        return self.safe_balance(balance)

    def parse_order_status(self, status):
        statuses = {
            'open': 'open',
            'filled': 'closed',
            'canceled': 'canceled',
            'cancelled': 'canceled',
            'rejected': 'rejected',
            'expired': 'expired',
        }
        return self.safe_string(statuses, status, status)

    def parse_order(self, order, market=None):
        market_id = self.safe_string(order, 'instrument_name')
        market = self.safe_market(market_id, market)
        symbol = market['symbol'] if market is not None else None
        timestamp = self._normalize_timestamp(self.safe_integer(order, 'creation_timestamp'))
        last_update = self._normalize_timestamp(self.safe_integer(order, 'last_update_timestamp'))
        side = self.safe_string(order, 'direction')
        type = self.safe_string(order, 'order_type')
        price = self.safe_number(order, 'price')
        amount = self.safe_number(order, 'amount')
        filled = self.safe_number(order, 'filled_amount')
        average = self.safe_number(order, 'average_price')
        status = self.parse_order_status(self.safe_string(order, 'order_state'))
        remaining = None
        if (amount is not None) and (filled is not None):
            remaining = max(amount - filled, 0)
        cost = None
        if (average is not None) and (filled is not None):
            cost = average * filled
        client_order_id = self.safe_string(order, 'label')
        return self.safe_order({
            'id': self.safe_string(order, 'order_id'),
            'clientOrderId': client_order_id,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'lastTradeTimestamp': last_update,
            'status': status,
            'symbol': symbol,
            'type': type,
            'side': side,
            'price': price,
            'amount': amount,
            'filled': filled,
            'remaining': remaining,
            'average': average,
            'cost': cost,
            'timeInForce': self.safe_string(order, 'time_in_force'),
            'postOnly': self.safe_bool(order, 'post_only'),
            'reduceOnly': self.safe_bool(order, 'reduce_only'),
            'info': order,
        }, market)

    def parse_trade(self, trade, market=None):
        market_id = self.safe_string(trade, 'instrument_name')
        market = self.safe_market(market_id, market)
        symbol = market['symbol'] if market is not None else None
        timestamp = self._normalize_timestamp(self.safe_integer(trade, 'timestamp'))
        fee = None
        fee_cost = self.safe_number(trade, 'fee')
        if fee_cost is not None:
            fee_currency = self.safe_currency_code(self.safe_string(trade, 'fee_coin_type'))
            fee = {
                'cost': fee_cost,
                'currency': fee_currency,
            }
        return self.safe_trade({
            'id': self.safe_string(trade, 'trade_id'),
            'orderId': self.safe_string(trade, 'order_id'),
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'symbol': symbol,
            'type': self.safe_string(trade, 'order_type'),
            'side': self.safe_string(trade, 'direction'),
            'price': self.safe_number(trade, 'price'),
            'amount': self.safe_number(trade, 'amount'),
            'takerOrMaker': self.safe_string(trade, 'role'),
            'fee': fee,
            'info': trade,
        }, market)

    def parse_position(self, position, market=None):
        market_id = self.safe_string(position, 'instrument_name')
        market = self.safe_market(market_id, market, None, 'swap')
        symbol = market['symbol'] if market is not None else None
        size = self.safe_number(position, 'size')
        direction = self.safe_string(position, 'direction')
        side = None
        if size is not None:
            side = 'short' if size < 0 else 'long'
        elif direction is not None:
            side = 'short' if direction == 'sell' else 'long'
        contracts = None
        if size is not None:
            contracts = abs(size)
        entry_price = self.safe_number_2(position, 'average_price', 'session_price')
        return self.safe_position({
            'info': position,
            'symbol': symbol,
            'timestamp': None,
            'datetime': None,
            'initialMargin': None,
            'initialMarginPercentage': None,
            'maintenanceMargin': None,
            'maintenanceMarginPercentage': None,
            'entryPrice': entry_price,
            'notional': None,
            'leverage': None,
            'unrealizedPnl': self.safe_number(position, 'floating_profit_loss'),
            'realizedPnl': self.safe_number(position, 'realized_profit_loss'),
            'contracts': contracts,
            'contractSize': None,
            'marginRatio': None,
            'liquidationPrice': None,
            'markPrice': self.safe_number(position, 'mark_price'),
            'lastPrice': None,
            'collateral': None,
            'marginMode': None,
            'side': side,
            'percentage': None,
            'hedged': None,
            'stopLossPrice': None,
            'takeProfitPrice': None,
        })

    async def create_order(self, symbol: str, type: str, side: str, amount: float, price=None, params={}):
        await self.load_markets()
        market = self.market(symbol)
        side = side.lower()
        if side not in ['buy', 'sell']:
            raise ExchangeError(self.id + ' createOrder() side must be "buy" or "sell"')
        request = {
            'instrument_name': market['id'],
            'amount': self.amount_to_precision(symbol, amount),
            'type': type,
        }
        if price is not None:
            request['price'] = self.price_to_precision(symbol, price)
        client_order_id = self.safe_string_2(params, 'clientOrderId', 'label')
        if client_order_id is not None:
            request['label'] = client_order_id
        time_in_force = self.safe_string_2(params, 'timeInForce', 'time_in_force')
        if time_in_force is not None:
            time_in_force_map = self.safe_value(self.options, 'timeInForce', {})
            request['time_in_force'] = self.safe_string(time_in_force_map, time_in_force, time_in_force)
        post_only = self.safe_value(params, 'postOnly')
        if post_only is None:
            post_only = self.safe_value(params, 'post_only')
        if post_only is not None:
            request['post_only'] = post_only
        reduce_only = self.safe_value(params, 'reduceOnly')
        if reduce_only is None:
            reduce_only = self.safe_value(params, 'reduce_only')
        if reduce_only is not None:
            request['reduce_only'] = reduce_only
        params = self.omit(params, ['clientOrderId', 'clientOrderID', 'label', 'timeInForce', 'time_in_force', 'postOnly', 'post_only', 'reduceOnly', 'reduce_only'])
        method = self.private_post_buy if side == 'buy' else self.private_post_sell
        response = await method(self.extend(request, params))
        result = self.safe_value(response, 'result', {})
        order = self.safe_value(result, 'order', {})
        order_id = self.safe_string(order, 'order_id')
        order = self.extend(order, request)
        order['order_id'] = order_id
        return self.parse_order(order, market)

    async def cancel_order(self, id: str, symbol: str = None, params={}):
        request = {
            'order_id': id,
        }
        response = await self.private_post_cancel(self.extend(request, params))
        result = self.safe_value(response, 'result', {})
        order_id = self.safe_string(result, 'order_id', id)
        market = None
        if symbol is not None:
            await self.load_markets()
            market = self.market(symbol)
        return self.parse_order({
            'order_id': order_id,
            'order_state': 'canceled',
            'instrument_name': market['id'] if market is not None else None,
        }, market)

    async def cancel_all_orders(self, symbol: str = None, params={}):
        await self.load_markets()
        request = {}
        if symbol is not None:
            market = self.market(symbol)
            request['instrument_name'] = market['id']
            return await self.private_post_cancel_all_by_instrument(self.extend(request, params))
        market_type, params = self.handle_market_type_and_params('cancelAllOrders', None, params)
        currency = self.safe_string(params, 'currency')
        if currency is None:
            if market_type is None:
                market_type = self.safe_string(self.options, 'defaultType', 'spot')
            currency = 'PERPETUAL' if market_type in ['swap', 'perpetual'] else 'SPOT'
        params = self.omit(params, 'currency')
        request['currency'] = currency
        return await self.private_post_cancel_all_by_currency(self.extend(request, params))

    async def fetch_order(self, id: str, symbol: str = None, params={}):
        request = {
            'order_id': id,
        }
        response = await self.private_post_get_order_state(self.extend(request, params))
        result = self.safe_value(response, 'result', {})
        market = None
        if symbol is not None:
            await self.load_markets()
            market = self.market(symbol)
        return self.parse_order(result, market)

    async def fetch_open_orders(self, symbol: str = None, since=None, limit=None, params={}):
        await self.load_markets()
        request = {}
        market = None
        if symbol is not None:
            market = self.market(symbol)
            request['instrument_name'] = market['id']
            response = await self.private_post_get_open_orders_by_instrument(self.extend(request, params))
        else:
            market_type, params = self.handle_market_type_and_params('fetchOpenOrders', None, params)
            currency = self.safe_string(params, 'currency')
            if currency is None:
                if market_type is None:
                    market_type = self.safe_string(self.options, 'defaultType', 'spot')
                currency = 'PERPETUAL' if market_type in ['swap', 'perpetual'] else 'SPOT'
            params = self.omit(params, 'currency')
            request['currency'] = currency
            response = await self.private_post_get_open_orders_by_currency(self.extend(request, params))
        result = self.safe_list(response, 'result', [])
        return self.parse_orders(result, market, since, limit)

    async def fetch_orders(self, symbol: str = None, since=None, limit=None, params={}):
        await self.load_markets()
        request = {}
        market = None
        if limit is not None:
            request['count'] = limit
        if symbol is not None:
            market = self.market(symbol)
            request['instrument_name'] = market['id']
            response = await self.private_post_get_order_history_by_instrument(self.extend(request, params))
        else:
            market_type, params = self.handle_market_type_and_params('fetchOrders', None, params)
            currency = self.safe_string(params, 'currency')
            if currency is None:
                if market_type is None:
                    market_type = self.safe_string(self.options, 'defaultType', 'spot')
                currency = 'PERPETUAL' if market_type in ['swap', 'perpetual'] else 'SPOT'
            params = self.omit(params, 'currency')
            request['currency'] = currency
            response = await self.private_post_get_order_history_by_currency(self.extend(request, params))
        result = self.safe_list(response, 'result', [])
        return self.parse_orders(result, market, since, limit)

    async def fetch_my_trades(self, symbol: str = None, since=None, limit=None, params={}):
        await self.load_markets()
        request = {}
        market = None
        if since is not None:
            request['start_timestamp'] = since
        if limit is not None:
            request['count'] = limit
        order_id = self.safe_string_2(params, 'order_id', 'orderId')
        if order_id is not None:
            params = self.omit(params, ['order_id', 'orderId'])
            request['order_id'] = order_id
            response = await self.private_post_get_user_trades_by_order(self.extend(request, params))
        elif symbol is not None:
            market = self.market(symbol)
            request['instrument_name'] = market['id']
            response = await self.private_post_get_user_trades_by_instrument(self.extend(request, params))
        else:
            market_type, params = self.handle_market_type_and_params('fetchMyTrades', None, params)
            currency = self.safe_string(params, 'currency')
            if currency is None:
                if market_type is None:
                    market_type = self.safe_string(self.options, 'defaultType', 'spot')
                currency = 'PERPETUAL' if market_type in ['swap', 'perpetual'] else 'SPOT'
            params = self.omit(params, 'currency')
            request['currency'] = currency
            response = await self.private_post_get_user_trades_by_currency(self.extend(request, params))
        result = self.safe_value(response, 'result', {})
        trades = self.safe_list(result, 'trades', result)
        return self.parse_trades(trades, market, since, limit)

    async def fetch_positions(self, symbols=None, params={}):
        await self.load_markets()
        market_type, params = self.handle_market_type_and_params('fetchPositions', None, params)
        currency = self.safe_string(params, 'currency')
        if currency is None:
            if market_type is None:
                market_type = self.safe_string(self.options, 'defaultType', 'spot')
            if market_type in ['swap', 'perpetual']:
                currency = 'PERPETUAL'
            else:
                currency = 'SPOT'
        params = self.omit(params, 'currency')
        request = {
            'currency': currency,
        }
        response = await self.private_post_get_positions(self.extend(request, params))
        result = self.safe_list(response, 'result', [])
        positions = []
        for position in result:
            positions.append(self.parse_position(position))
        return self.filter_by_array_positions(positions, 'symbol', self.market_symbols(symbols), False)

    async def close_position(self, symbol: str, side: str = None, params={}):
        await self.load_markets()
        market = self.market(symbol)
        request = {
            'instrument_name': market['id'],
        }
        order_type = self.safe_string(params, 'type')
        if order_type is not None:
            request['type'] = order_type
        price = self.safe_number(params, 'price')
        if price is not None:
            request['price'] = self.price_to_precision(symbol, price)
        params = self.omit(params, ['type', 'price'])
        response = await self.private_post_close_position(self.extend(request, params))
        result = self.safe_value(response, 'result', {})
        order = self.safe_value(result, 'order', {})
        order_id = self.safe_string(order, 'order_id')
        order = self.extend(order, request)
        order['order_id'] = order_id
        return self.parse_order(order, market)

    def sign(self, path, api='public', method='POST', params={}, headers=None, body=None):
        url = self.urls['api'][api] + '/' + api + '/' + path
        if method == 'GET':
            if params:
                url += '?' + self.urlencode(params)
        else:
            if (api == 'private') and (not self.safe_string(params, 'jsonrpc')):
                params = {
                    'jsonrpc': '2.0',
                    'id': self.nonce(),
                    'method': '/' + api + '/' + path,
                    'params': params,
                }
            body = self.json(params) if params else None
            headers = {
                'Content-Type': 'application/json',
            }
        if api == 'private':
            if headers is None:
                headers = {}
            self.check_required_credentials()
            expires = self.safe_integer(self.options, 'expires')
            if (expires is not None) and (expires < self.milliseconds()):
                raise AuthenticationError(self.id + ' access token expired, call signIn() method')
            token = self.safe_string(self.options, 'accessToken')
            if token is None:
                raise AuthenticationError(self.id + ' missing access token in options["accessToken"]')
            headers['Authorization'] = 'Bearer ' + token
        return {'url': url, 'method': method, 'body': body, 'headers': headers}

    def handle_errors(self, httpCode, reason, url, method, headers, body, response, requestHeaders, requestBody):
        if response is None:
            return None
        error = self.safe_value(response, 'error')
        if error is not None:
            code = self.safe_string(error, 'code')
            message = self.safe_string(error, 'message')
            feedback = self.id + ' ' + self.json({'code': code, 'message': message})
            self.throw_exactly_matched_exception(self.safe_value(self.exceptions, 'exact', {}), code, feedback)
            raise ExchangeError(feedback)
        return None
