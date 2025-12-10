# kalshi_bot/core/client.py
import asyncio
import json
import websockets
import requests
from dataclasses import dataclass
from typing import Dict, Callable, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import time
import base64
import pandas as pd

from kalshi_bot.core.data.order_book import OrderBook
from kalshi_bot.core.delta_recorder import DeltaRecorder
from kalshi_bot.strategy.sweep import Sweep
from kalshi_bot.util.util import get_signed_headers, get_nba_sport_markets
from kalshi_bot.util.load_credential import load_credentials
from kalshi_bot.util.logger import get_logger

TARGET_TICKER = "KXNFLGAME-25DEC04DALDET-DET"

LOGIN_URL = "https://api.kalshi.com/trade/api/v2/login"
WS_URL = "wss://live-api-v2.kalshi.com/trade/api/v2/ws"

logger = get_logger('kalshi_client')

class KalshiClient:
    def __init__(self, api_key: str, pk: str):
        self.api_key = api_key
        self.pk = pk
        self.ws_url = "wss://api.elections.kalshi.com/trade-api/ws/v2"
        self.on_update = lambda x: None
        self.sweep = Sweep()
        self.markets_ticket_map = {i.ticker: i for i in get_nba_sport_markets()}
        self.target_tickers = [i for i in self.markets_ticket_map.keys()]
        self.sid = None
        self.order_recorders = {i: DeltaRecorder(ticker=i) for i in self.target_tickers}
        self.order_book_cache = {i: OrderBook(i) for i in self.target_tickers}
        

    def _auth_headers(self) -> Dict[str, str]:
        """Generate correct WebSocket auth headers (PKCS1v15, ms timestamp)."""
        private_key = serialization.load_pem_private_key(self.pk)
        
        timestamp = str(int(time.time() * 1000))  # Milliseconds!
        payload = timestamp + "GET" + "/trade-api/ws/v2"  # Exact payload for connect
        
        signature = private_key.sign(
            payload.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),  # Changed from PSS to PKCS1v15
            hashes.SHA256()
        )
        
        return {
            "KALSHI-ACCESS-KEY": self.api_key,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode('utf-8'),
        }

    async def start(self):
        headers = self._auth_headers()
        print(f"Connecting with timestamp: {headers['KALSHI-ACCESS-TIMESTAMP']}")

        for recorder in self.order_recorders.values():
            await recorder.start()          # ← this is the magic line
        
        try:
            async with websockets.connect(self.ws_url, extra_headers=headers) as ws:
                print("✅ WebSocket connected!")
                
                # Initial subscribe (first ticker)
                await self._subscribe_tickers(ws)  # Now with "id":1
                
                # Wait for confirmation (poll first few messages)
                confirmation_received = False
                for _ in range(5):  # Short timeout
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        data = json.loads(msg)
                        if data.get("type") == "subscribed" and data.get("id") == 1:
                            print(f"✅ Initial sub confirmed: {data.get('subscriptions')}")
                            # Extract sid from response, e.g., data["subscriptions"][0]["sid"]
                            self.sid = data["msg"]["sid"]  # Assume first channel
                            confirmation_received = True
                            break
                    except asyncio.TimeoutError:
                        pass
                
                if not confirmation_received:
                    raise ValueError("No sub confirmation—check auth/id")
                
                # Now add remaining tickers
                if len(self.target_tickers) > 1:
                    markets_to_add = self.target_tickers[1:]
                    update_msg = {
                        "id": 2,
                        "cmd": "update_subscription",
                        "params": {
                            "sids": [self.sid],  # Dynamic from response!
                            "market_tickers": markets_to_add,
                            "action": "add_markets"
                        }
                    }
                    await ws.send(json.dumps(update_msg))
                    print("📤 Update sub sent")
                
                # SINGLE FOREVER LOOP: Handle all ongoing messages
                async for message in ws:
                    await self._handle_message(message)
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"❌ Connection failed: {e.status_code} - {e.response_headers}")
            print("Fix: Regenerate API key/private key at kalshi.com/account/api and ensure PEM is clean.")
        except Exception as e:
            print(f"❌ WS error: {e}")

    async def _subscribe_tickers(self, ws):
        """Subscribe to all ticker updates (prices, volume)."""
        subscribe_msg = {
            "id": 1,
            "cmd": "subscribe",
            "params": {"channels": ["orderbook_delta"],
            "market_ticker": self.target_tickers[0]}
        }
        await ws.send(json.dumps(subscribe_msg))

    async def _handle_message(self, msg: str):
        """Process incoming messages and trigger on_update."""
        data = json.loads(msg)
        msg_type = data.get("type")
        payload = data['msg']
        if msg_type == "ok":
            print(f"✅ Subscription confirmed!")

        elif msg_type == 'orderbook_snapshot':
            logger.info(f"Applying Snapshot to: {payload['market_ticker']}")
            mt = payload['market_ticker']
            self.order_book_cache[mt].apply_snapshot(payload, data['seq'])
            bbid, bask = self.order_book_cache[mt].best_bid(), self.order_book_cache[mt].best_ask()
            bid_vol, ask_vol = self.order_book_cache[mt].bid_volume(), self.order_book_cache[mt].ask_volume()
            mid = self.order_book_cache[mt].mid()
            top_n = self.order_book_cache[mt].top_n(5)
            # update tracker
            await self.order_recorders[mt].log_snapshot(data['seq'], bbid=bbid, bask=bask, mid=mid, bid_vol=bid_vol, ask_vol=ask_vol, top_n=top_n)

        elif msg_type == "orderbook_delta":
            mt = payload['market_ticker']
            self.order_book_cache[mt].apply_delta(update=payload, seq=data['seq'])
            # Update tracker
            bbid, bask = self.order_book_cache[mt].best_bid(), self.order_book_cache[mt].best_ask()
            bid_vol, ask_vol = self.order_book_cache[mt].bid_volume(), self.order_book_cache[mt].ask_volume()
            mid = self.order_book_cache[mt].mid()
            top_n = self.order_book_cache[mt].top_n(5)
            await self.order_recorders[mt].log_delta(delta_msg=payload, seq=data['seq'], bbid=bbid, bask=bask, mid=mid, bid_vol=bid_vol, ask_vol=ask_vol, top_n=top_n)
        else:
            print(f"📨 Other: {data}")

if __name__ == "__main__":
    api_key, pk = load_credentials()
    client = KalshiClient(
        api_key=api_key,
        private_key_path=pk
    )
    #client.on_update = on_price_update
    asyncio.run(client.start())