# -*- coding: utf-8 -*-

from ccxt.async_support.binance import binance
from ccxt.abstract.aster import ImplicitAPI
from ccxt.base.types import Any
from ccxt.base.exchange import Exchange as SyncExchange


class aster(ImplicitAPI, binance):

    def describe(self) -> Any:
        return self.deep_extend(super(aster, self).describe(), {
            'id': 'aster',
            'name': 'Aster',
            'countries': [],
            'certified': False,
            'pro': False,
            'version': 'v1',
            'has': self.deep_extend(super(aster, self).describe().get('has', {}), {
                'margin': False,
                'swap': True,
                'future': False,
                'option': False,
                'fetchOrder': True,
                'fetchOrders': True,
                'fetchOpenOrders': True,
            }),
            'urls': {
                'logo': None,
                'api': {
                    'public': 'https://sapi.asterdex.com/api/v1',
                    'private': 'https://sapi.asterdex.com/api/v1',
                    'sapi': 'https://sapi.asterdex.com/api/v1',
                    'fapiPublic': 'https://fapi.asterdex.com/fapi/v1',
                    'fapiPublicV2': 'https://fapi.asterdex.com/fapi/v2',
                    'fapiPublicV3': 'https://fapi.asterdex.com/fapi/v3',
                    'fapiPrivate': 'https://fapi.asterdex.com/fapi/v1',
                    'fapiPrivateV2': 'https://fapi.asterdex.com/fapi/v2',
                    'fapiPrivateV3': 'https://fapi.asterdex.com/fapi/v3',
                    'fapiData': 'https://fapi.asterdex.com/futures/data',
                    'dapiPublic': None,
                    'dapiPrivate': None,
                    'dapiData': None,
                    'eapiPublic': None,
                    'eapiPrivate': None,
                },
                'www': 'https://asterdex.com',
                'doc': 'https://sapi.asterdex.com',
            },
            'options': self.deep_extend(super(aster, self).describe().get('options', {}), {
                'defaultType': 'spot',
                'defaultSubType': 'linear',
                'quoteOrderQty': False,
                'fetchCurrencies': False,
                'fetchMargins': False,
                'fetchMarkets': { 'types': ['spot', 'linear'] },
            }),
        })

    # Normalize high-precision timestamps (µs/ns) to milliseconds
    def iso8601(self, timestamp=None):
        if timestamp is None:
            return timestamp
        if not isinstance(timestamp, int):
            return SyncExchange.iso8601(timestamp)
        ts = int(timestamp)
        if ts > 100000000000000000:  # ns -> ms
            ts //= 1000000
        elif ts > 100000000000000:   # µs -> ms
            ts //= 1000
        elif ts < 100000000000:      # s -> ms
            ts *= 1000
        return SyncExchange.iso8601(ts)

    async def fetch_balance(self, params={}):
        data = await super(aster, self).fetch_balance(params)
        # Ensure standard CCXT balance structure: free/used/total dicts
        free = self.safe_value(data, 'free')
        used = self.safe_value(data, 'used')
        total = self.safe_value(data, 'total')
        if not isinstance(free, dict) or not isinstance(used, dict) or not isinstance(total, dict):
            free, used, total = ({}, {}, {})
        if (len(free) == 0 and len(used) == 0 and len(total) == 0):
            info = self.safe_value(data, 'info', {})
            balances = self.safe_list(info, 'balances', [])
            for entry in balances:
                asset = self.safe_string(entry, 'asset')
                code = self.safe_currency_code(asset)
                free_amount = self.safe_number(entry, 'free')
                locked_amount = self.safe_number(entry, 'locked')
                if free_amount is None:
                    try:
                        free_amount = float(self.safe_string(entry, 'free'))
                    except Exception:
                        free_amount = 0.0
                if locked_amount is None:
                    try:
                        locked_amount = float(self.safe_string(entry, 'locked'))
                    except Exception:
                        locked_amount = 0.0
                total_amount = (free_amount or 0.0) + (locked_amount or 0.0)
                free[code] = free_amount or 0.0
                used[code] = locked_amount or 0.0
                total[code] = total_amount
            data['free'] = free
            data['used'] = used
            data['total'] = total
        # Normalize timestamp to ms and set datetime
        ts = self.safe_integer(data, 'timestamp')
        if ts is not None:
            norm = ts
            if norm > 100000000000000000:
                norm //= 1000000
            elif norm > 100000000000000:
                norm //= 1000
            elif norm < 100000000000:
                norm *= 1000
            data['timestamp'] = norm
            data['datetime'] = SyncExchange.iso8601(norm)
        return data







