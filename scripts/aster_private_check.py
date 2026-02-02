#!/usr/bin/env python3

import os
import sys
import time
import json


def add_local_ccxt_to_path():
    root = os.path.dirname(os.path.abspath(__file__))
    python_dir = os.path.join(os.path.dirname(root), 'python')
    if os.path.isdir(python_dir):
        sys.path.insert(0, python_dir)


def load_config(path):
    with open(path, 'r', encoding='utf-8-sig') as fh:
        return json.load(fh)


def pick_symbol(markets, preferred_list, market_type):
    for s in preferred_list:
        if s and s in markets:
            return s
    for m in markets.values():
        if market_type == 'swap' and m.get('swap'):
            return m['symbol']
        if market_type == 'spot' and m.get('spot'):
            return m['symbol']
    return None


def compute_safe_price_and_amount(ex, market, side, offset, desired_quote_cost):
    symbol = market['symbol']
    # base a target price on last or orderbook mid
    ticker = None
    try:
        ticker = ex.fetch_ticker(symbol)
    except Exception:
        ticker = {}
    last = ticker.get('last')
    if last is None:
        ob = ex.fetch_order_book(symbol, limit=5)
        bids = ob.get('bids') or []
        asks = ob.get('asks') or []
        if bids and asks:
            last = (bids[0][0] + asks[0][0]) / 2
        elif bids:
            last = bids[0][0]
        elif asks:
            last = asks[0][0]
        else:
            raise RuntimeError('No market price reference available')
    # ensure numeric
    price = float(last)
    if side == 'buy':
        price = price * (1.0 - float(offset))
    else:
        price = price * (1.0 + float(offset))
    # adhere to precision and min/max limits
    price = float(ex.price_to_precision(symbol, price))
    min_amt = None
    if market.get('limits') and market['limits'].get('amount'):
        min_amt = market['limits']['amount'].get('min')
    min_cost = None
    if market.get('limits') and market['limits'].get('cost'):
        min_cost = market['limits']['cost'].get('min')

    amount = None
    # If we have a desired quote cost, derive amount = cost/price
    if desired_quote_cost and price > 0:
        amount = float(desired_quote_cost) / price
    # Enforce min_cost
    if (amount is None) and (min_cost is not None) and price > 0:
        amount = float(min_cost) / price * 1.05
    # Fallback to min_amt or small value
    if amount is None:
        amount = min_amt if min_amt is not None else 1.0
    # Add small margin and quantize by amount precision
    amount = amount * 1.05
    amount = float(ex.amount_to_precision(symbol, amount))
    return price, amount


def main():
    add_local_ccxt_to_path()
    import ccxt  # noqa: E402

    config_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'aster_private_config.json')
    if not os.path.isfile(config_path):
        # fallback to example if user didn't create one
        example_path = os.path.join(os.path.dirname(__file__), 'aster_private_config.example.json')
        print('Config not found:', config_path)
        print('Please create it. Example at:', example_path)
        sys.exit(1)

    cfg = load_config(config_path)
    apiKey = cfg.get('apiKey')
    secret = cfg.get('secret')
    if not apiKey or not secret:
        print('apiKey/secret missing in config:', config_path)
        sys.exit(1)

    market_type = (cfg.get('marketType') or 'spot').lower()

    ex = ccxt.aster({
        'apiKey': apiKey,
        'secret': secret,
        'timeout': cfg.get('timeout', 20000),
        'options': {
            'recvWindow': cfg.get('recvWindow', 5000),
            'defaultType': market_type,
        }
    })

    preferred_symbol = cfg.get('symbol')
    side = (cfg.get('side') or 'buy').lower()
    price_offset = float(cfg.get('priceOffset', 0.30))
    desired_quote_cost = float(cfg.get('testOrderQuoteCost', 10.0))

    print('Using exchange:', ex.id)

    # sanity private ping via balance
    try:
        bal = ex.fetch_balance()
        total_assets = [k for k, v in (bal.get('total') or {}).items() if v]
        print('fetch_balance: assets with nonzero total:', ','.join(total_assets[:10]), '...')
    except Exception as e:
        print('fetch_balance error:', e)

    # markets
    markets = ex.load_markets()
    if market_type == 'swap':
        fallback = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'BNB/USDT:USDT']
    else:
        fallback = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
    symbol = pick_symbol(markets, [preferred_symbol] + fallback, market_type)
    if not symbol:
        print(f'No suitable {market_type} symbol found')
        sys.exit(1)
    market = markets[symbol]
    print('Symbol:', symbol)

    # compute price to avoid execution and a minimal amount
    price, amount = compute_safe_price_and_amount(ex, market, side, price_offset, desired_quote_cost)
    print(f'Placing {side} limit order: amount={amount}, price={price}')

    # Rough balance check to avoid InsufficientFunds
    try:
        bal = ex.fetch_balance()
        if side == 'buy':
            quote = market['quote']
            need = amount * price
            have = float((bal.get(quote) or {}).get('free') or 0)
            print(f'Free {quote}:', have, 'Needed:', need)
            if have < need:
                print('Insufficient free quote balance; skipping create_order')
                return
        else:
            base = market['base']
            need = amount
            have = float((bal.get(base) or {}).get('free') or 0)
            print(f'Free {base}:', have, 'Needed:', need)
            if have < need:
                print('Insufficient free base balance; skipping create_order')
                return
    except Exception as e:
        print('Balance pre-check failed, will try to place anyway:', e)

    order = None
    try:
        order = ex.create_order(symbol, 'limit', side, amount, price)
        print('create_order OK:', order.get('id'))
    except Exception as e:
        print('create_order error:', e)
        return

    oid = order.get('id')
    try:
        fetched = ex.fetch_order(oid, symbol)
        print('fetch_order status:', fetched.get('status'))
    except Exception as e:
        print('fetch_order error:', e)

    try:
        open_orders = ex.fetch_open_orders(symbol)
        print('fetch_open_orders count:', len(open_orders))
    except Exception as e:
        print('fetch_open_orders error:', e)

    try:
        hist = ex.fetch_orders(symbol, limit=10)
        print('fetch_orders recent count:', len(hist))
    except Exception as e:
        print('fetch_orders error:', e)

    # cleanup: cancel
    try:
        ex.cancel_order(oid, symbol)
        print('cancel_order sent for:', oid)
        time.sleep(1.0)
        fetched2 = ex.fetch_order(oid, symbol)
        print('post-cancel fetch_order status:', fetched2.get('status'))
    except Exception as e:
        print('cancel/fetch after cancel error:', e)

    print('Done.')


if __name__ == '__main__':
    main()

