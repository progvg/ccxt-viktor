# -*- coding: utf-8 -*-

from ccxt.binance import binance
from ccxt.abstract.aster import ImplicitAPI
from ccxt.base.types import Any
from ccxt.base.errors import AuthenticationError, InvalidNonce, ArgumentsRequired, BadRequest
from ccxt.base.errors import InvalidAddress, NotSupported


class aster(ImplicitAPI, binance):

    def describe(self) -> Any:
        parent = super(aster, self).describe()
        return self.deep_extend(parent, {
            'id': 'aster',
            'name': 'Aster',
            'countries': [],
            'certified': False,
            'pro': False,
            'version': 'v1',
            'has': self.deep_extend(parent.get('has', {}), {
                'margin': False,
                'swap': False,
                'future': False,
                'option': False,
                'fetchOrder': True,
                'fetchOrders': True,
                'fetchOpenOrders': True,
                'withdraw': True,
                'transfer': True,
                'fetchDeposits': False,
                'fetchWithdrawals': False,
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
            'options': self.deep_extend(parent.get('options', {}), {
                'defaultType': 'spot',
                'quoteOrderQty': False,
                'fetchCurrencies': False,
                'fetchMargins': False,
                'fetchMarkets': {'types': ['spot']},
            }),
            'exceptions': self.deep_extend(parent.get('exceptions', {}), {
                'exact': {
                    '-2008': AuthenticationError,  # Invalid Api-Key ID
                    '-1021': InvalidNonce,         # INVALID_TIMESTAMP
                    '-1022': AuthenticationError,  # INVALID_SIGNATURE
                    '-1102': ArgumentsRequired,
                    '-1103': BadRequest,
                    '-1116': BadRequest,
                    '-1117': BadRequest,
                },
            }),
        })

    def withdraw(self, code: str, amount, address: str, tag=None, params={}):
        self.load_markets()
        if not address:
            raise InvalidAddress(self.id + ' withdraw() requires a receiver address')
        currency = self.currency(code)
        chain_id = self.safe_string(params, 'chainId')
        if chain_id is None:
            raise ArgumentsRequired(self.id + " withdraw() requires 'chainId' in params (1=ETH,56=BSC,42161=Arbi)")
        receiver = self.safe_string(params, 'receiver', address)
        fee = self.safe_string(params, 'fee')
        request = {
            'chainId': chain_id,
            'asset': currency['id'],
            'amount': self.currency_to_precision(code, amount),
            'receiver': receiver,
        }
        if fee is None:
            try:
                est = self.public_get_aster_withdraw_estimatefee({'chainId': chain_id, 'asset': currency['id']})
                fee = self.safe_string(est, 'gasCost')
            except Exception:
                pass
        if fee is None:
            raise ArgumentsRequired(self.id + " withdraw() requires 'fee' (use estimateFee endpoint to fetch)")
        request['fee'] = fee
        user_signature = self.safe_string(params, 'userSignature')
        if user_signature is None:
            raise ArgumentsRequired(self.id + " withdraw() requires 'userSignature' (EIP-712 typed signature per docs)")
        nonce = self.safe_string(params, 'nonce', self.number_to_string(self.milliseconds() * 1000))
        request['nonce'] = nonce
        request['userSignature'] = user_signature
        request['timestamp'] = self.milliseconds()
        recv_window = self.safe_integer(params, 'recvWindow')
        if recv_window is not None:
            request['recvWindow'] = recv_window
        response = self.private_post_aster_user_withdraw(self.extend(request, self.omit(params, ['chainId', 'receiver', 'fee', 'userSignature', 'nonce'])))
        return self.parse_transaction(response, currency)

    def parse_transaction(self, transaction, currency=None):
        id = self.safe_string_2(transaction, 'withdrawId', 'id')
        txid = self.safe_string_2(transaction, 'hash', 'txid')
        code = None
        if currency is not None:
            code = currency['code']
        return {
            'info': transaction,
            'id': id,
            'txid': txid,
            'timestamp': None,
            'datetime': None,
            'network': None,
            'addressFrom': None,
            'address': None,
            'addressTo': None,
            'tagFrom': None,
            'tag': None,
            'tagTo': None,
            'type': 'withdrawal',
            'amount': None,
            'currency': code,
            'status': None,
            'updated': None,
            'fee': None,
        }

    def transfer(self, code: str, amount, fromAccount: str, toAccount: str, params={}):
        self.load_markets()
        currency = self.currency(code)
        ts = self.milliseconds()
        fromLower = (fromAccount or '').lower()
        toLower = (toAccount or '').lower()
        def is_future(name):
            return name in ['future', 'futures', 'swap', 'perp', 'contract']
        if fromLower == toLower:
            raise BadRequest(self.id + ' transfer() fromAccount and toAccount cannot be the same')
        if fromLower in ['spot', 'exchange'] and is_future(toLower):
            kindType = 'SPOT_FUTURE'
        elif is_future(fromLower) and toLower in ['spot', 'exchange']:
            kindType = 'FUTURE_SPOT'
        else:
            raise NotSupported(self.id + ' transfer() supports only between spot and futures (perp) accounts')
        client_tran_id = self.safe_string(params, 'clientTranId', self.number_to_string(ts))
        request = {
            'amount': self.currency_to_precision(code, amount),
            'asset': currency['id'],
            'clientTranId': client_tran_id,
            'kindType': kindType,
            'timestamp': ts,
        }
        response = self.private_post_asset_wallet_transfer(self.extend(request, self.omit(params, ['clientTranId'])))
        return {
            'info': response,
            'id': self.safe_string(response, 'tranId'),
            'amount': amount,
            'code': currency['code'],
            'fromAccount': fromAccount,
            'toAccount': toAccount,
            'timestamp': ts,
            'datetime': self.iso8601(ts),
            'status': self.safe_string_lower(response, 'status'),
        }
