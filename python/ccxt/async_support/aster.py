# -*- coding: utf-8 -*-

from ccxt.async_support.binance import binance
from ccxt.abstract.aster import ImplicitAPI
from ccxt.base.types import Any


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
                'swap': False,
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
                },
                'www': 'https://asterdex.com',
                'doc': 'https://sapi.asterdex.com',
            },
            'options': self.deep_extend(super(aster, self).describe().get('options', {}), {
                'defaultType': 'spot',
                'quoteOrderQty': False,
                'fetchCurrencies': False,
                'fetchMargins': False,
                'fetchMarkets': { 'types': ['spot'] },
            }),
        })








