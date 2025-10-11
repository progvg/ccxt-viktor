#!/usr/bin/env python3

import os
import sys
import json
import time
import asyncio

import requests
import aiohttp

API_BASE = 'https://sapi.asterdex.com/api/v1'
WS_BASE = 'wss://sstream.asterdex.com/ws'

def load_config(path):
    with open(path, 'r', encoding='utf-8-sig') as fh:
        return json.load(fh)

def get_listen_key(api_key: str):
    url = f'{API_BASE}/listenKey'
    r = requests.post(url, headers={'X-MBX-APIKEY': api_key}, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get('listenKey') or data.get('listen_key')

async def ws_dump(listen_key: str, timeout_sec: int = 120):
    url = f'{WS_BASE}/{listen_key}'
    print('Connecting to:', url)
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url, heartbeat=25) as ws:
            start = time.time()
            while time.time() - start < timeout_sec:
                try:
                    msg = await ws.receive(timeout=timeout_sec)
                except asyncio.TimeoutError:
                    print('WS timeout waiting for message')
                    break
                if msg.type == aiohttp.WSMsgType.TEXT:
                    print('WS TEXT:', msg.data)
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    print('WS BINARY len:', len(msg.data))
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    print('WS CLOSED')
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print('WS ERROR:', msg.data)
                    break

def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'aster_private_config.json')
    cfg = load_config(cfg_path)
    api_key = cfg.get('apiKey')
    secret = cfg.get('secret')
    if not api_key or not secret:
        print('Missing apiKey/secret in config')
        sys.exit(1)
    listen_key = get_listen_key(api_key)
    if not listen_key:
        print('Failed to obtain listenKey')
        sys.exit(1)
    print('listenKey:', listen_key)
    try:
        import platform
        if platform.system() == 'Windows':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass
    asyncio.run(ws_dump(listen_key, int(os.environ.get('ASTER_WS_TIMEOUT', '120'))))

if __name__ == '__main__':
    main()
