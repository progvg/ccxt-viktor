# -*- coding: utf-8 -*-

# CCXT Pro WebSocket support for Aster (Binance-like streaming API)

from ccxt.pro.binance import binance
from ccxt.base.types import Any

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

