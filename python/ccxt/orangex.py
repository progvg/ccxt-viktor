# -*- coding: utf-8 -*-

from ccxt.abstract.orangex import ImplicitAPI
from ccxt.base.types import Any
from ccxt.base.errors import AuthenticationError, ExchangeError
from ccxt.base.exchange import Exchange


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
                'fetchTickers': False,
                'fetchTime': True,
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
            'options': self.deep_extend(parent.get('options', {}), {
                'defaultType': 'spot',
                'fetchMarkets': {
                    'types': ['spot', 'swap'],
                },
            }),
        })

    # Normalize high-precision timestamps (us/ns) to milliseconds
    def iso8601(self, timestamp=None):
        if timestamp is None:
            return timestamp
        if not isinstance(timestamp, int):
            return Exchange.iso8601(timestamp)
        ts = self._normalize_timestamp(timestamp)
        return Exchange.iso8601(ts)

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

    def fetch_time(self, params={}):
        response = self.public_get_get_instruments(self.extend({'currency': 'SPOT'}, params))
        timestamp = self.safe_integer_2(response, 'usOut', 'usIn')
        return self._normalize_timestamp(timestamp)

    def fetch_markets(self, params={}):
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
        response = self.public_get_get_instruments(self.extend(request, params))
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

    def fetch_order_book(self, symbol: str, limit=None, params={}):
        self.load_markets()
        market = self.market(symbol)
        request = {
            'instrument_name': market['id'],
        }
        if limit is not None:
            request['depth'] = limit
        response = self.public_get_get_order_book(self.extend(request, params))
        result = self.safe_value(response, 'result', {})
        timestamp = self._normalize_timestamp(self.safe_integer(result, 'timestamp'))
        return self.parse_order_book(result, symbol, timestamp, 'bids', 'asks')

    def fetch_ticker(self, symbol: str, params={}):
        self.load_markets()
        market = self.market(symbol)
        request = {
            'instrument_name': market['id'],
        }
        response = self.public_get_tickers(self.extend(request, params))
        result = self.safe_value(response, 'result', [])
        ticker = result[0] if isinstance(result, list) and (len(result) > 0) else result
        return self.parse_ticker(ticker, market)

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

    def sign(self, path, api='public', method='POST', params={}, headers=None, body=None):
        url = self.urls['api'][api] + '/' + api + '/' + path
        if method == 'GET':
            if params:
                url += '?' + self.urlencode(params)
        else:
            body = self.json(params) if params else None
            headers = {
                'Content-Type': 'application/json',
            }
        if api == 'private':
            if headers is None:
                headers = {}
            self.check_required_credentials()
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
