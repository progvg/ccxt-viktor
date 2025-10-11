#!/usr/bin/env python3

import os
import sys
import asyncio
import json


def add_local_ccxt_to_path():
    root = os.path.dirname(os.path.abspath(__file__))
    python_dir = os.path.join(os.path.dirname(root), 'python')
    if os.path.isdir(python_dir):
        sys.path.insert(0, python_dir)


def load_config(path):
    with open(path, 'r', encoding='utf-8-sig') as fh:
        return json.load(fh)


def pick_symbol(markets, preferred_list):
    for s in preferred_list:
        if s and s in markets:
            return s
    for m in markets.values():
        if m.get('spot'):
            return m['symbol']
    return None


async def compute_safe_price_and_amount(ex, market, side, offset, desired_quote_cost):
    symbol = market['symbol']
    last = None
    try:
        t = await ex.fetch_ticker(symbol)
        last = t.get('last')
    except Exception:
        last = None
    if last is None:
        ob = await ex.fetch_order_book(symbol, limit=5)
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
    price = float(last)
    if side == 'buy':
        price = price * (1.0 - float(offset))
    else:
        price = price * (1.0 + float(offset))
    price = float(ex.price_to_precision(symbol, price))
    min_amt = None
    if market.get('limits') and market['limits'].get('amount'):
        min_amt = market['limits']['amount'].get('min')
    min_cost = None
    if market.get('limits') and market['limits'].get('cost'):
        min_cost = market['limits']['cost'].get('min')
    amount = None
    if desired_quote_cost and price > 0:
        amount = float(desired_quote_cost) / price
    if (amount is None) and (min_cost is not None) and price > 0:
        amount = float(min_cost) / price * 1.05
    if amount is None:
        amount = min_amt if min_amt is not None else 1.0
    amount = amount * 1.05
    amount = float(ex.amount_to_precision(symbol, amount))
    return price, amount


async def main():
    try:
        import platform
        if platform.system() == 'Windows':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

    add_local_ccxt_to_path()
    from ccxt import pro as ccxtpro  # noqa: E402

    config_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'aster_private_config.json')
    if not os.path.isfile(config_path):
        print('Config not found:', config_path)
        print('Create one from scripts/aster_private_config.example.json')
        return
    cfg = load_config(config_path)

    apiKey = cfg.get('apiKey')
    secret = cfg.get('secret')
    if not apiKey or not secret:
        print('apiKey/secret missing in config')
        return

    ex = ccxtpro.aster({
        'apiKey': apiKey,
        'secret': secret,
        'timeout': cfg.get('timeout', 20000),
        'options': {
            'recvWindow': cfg.get('recvWindow', 5000),
            'defaultType': 'spot',
        }
    })

    max_wait = int(os.environ.get('ASTER_WS_TIMEOUT', '90'))
    side = (cfg.get('side') or 'buy').lower()
    price_offset = float(cfg.get('priceOffset', 0.30))
    desired_quote_cost = float(cfg.get('testOrderQuoteCost', 10.0))

    print('Using exchange (pro):', ex.id)

    await ex.load_markets()
    preferred_symbol = cfg.get('symbol')
    symbol = pick_symbol(ex.markets, [preferred_symbol, 'BTC/USDT', 'ETH/USDT', 'BNB/USDT'])
    if not symbol:
        print('No suitable spot symbol found')
        await ex.close()
        return
    market = ex.markets[symbol]
    print('Symbol:', symbol)

    received_for_id = []
    order_id_holder = {'id': None}

    async def orders_consumer():
        nonlocal received_for_id
        while True:
            updates = await ex.watch_orders()
            for u in updates or []:
                oid = u.get('id')
                sid = order_id_holder['id']
                status = u.get('status')
                if sid is None or oid == sid:
                    print(f"order event: id={oid} status={status} side={u.get('side')} type={u.get('type')} amount={u.get('amount')} price={u.get('price')}")
                    if sid is not None and oid == sid:
                        received_for_id.append(status)

    consumer_task = asyncio.create_task(orders_consumer())

    price, amount = await compute_safe_price_and_amount(ex, market, side, price_offset, desired_quote_cost)
    print(f'Creating {side} limit order: amount={amount}, price={price}')

    try:
        order = await ex.create_order(symbol, 'limit', side, amount, price)
        oid = order.get('id')
        order_id_holder['id'] = oid
        print('create_order OK:', oid)
    except Exception as e:
        print('create_order error:', e)
        consumer_task.cancel()
        try:
            await consumer_task
        except Exception:
            pass
        await ex.close()
        return

    # allow initial event(s)
    await asyncio.sleep(2)

    try:
        await ex.cancel_order(order_id_holder['id'], symbol)
        print('cancel_order sent for:', order_id_holder['id'])
    except Exception as e:
        print('cancel_order error:', e)

    try:
        await asyncio.sleep(max_wait)
    except asyncio.TimeoutError:
        pass

    consumer_task.cancel()
    try:
        await consumer_task
    except Exception:
        pass
    await ex.close()
    print('Done. Received statuses for order:', received_for_id)


if __name__ == '__main__':
    try:
        import platform
        if platform.system() == 'Windows':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass
    asyncio.run(main())


