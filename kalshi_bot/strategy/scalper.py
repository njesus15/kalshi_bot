# strategy/arbitrage_scalper.py
import asyncio
import time
from typing import Dict, Callable
from data.order_book import OrderBook

class ArbitrageScalper:
    def __init__(self):
        self.positions: Dict[str, int] = {}  # ticker → net YES contracts
        self.last_quote: Dict[str, float] = {}
        self.active_hedges: set = set()

    def microprice(self, ob: OrderBook) -> float:
        top = ob.top_n(1)
        bid, bid_sz = (top["bids"][0] if top["bids"] else (ob.best_bid(), 0))
        ask, ask_sz = (top["asks"][0] if top["asks"] else (ob.best_ask(), 0))
        total = bid_sz + ask_sz
        return (bid * ask_sz + ask * bid_sz) / total if total > 0 else ob.mid()

    async def send_order(self, ws, msg: dict):
        await ws.send(json.dumps(msg))

    async def place_limit(self, ws, ticker: str, side: str, price: float, size: int):
        await self.send_order(ws, {
            "cmd": "create_order",
            "params": {
                "ticker": ticker,
                "side": side,
                "type": "limit",
                "price": round(price, 3),
                "size": size
            }
        })

    async def cancel_all(self, ws, ticker: str = None):
        msg = {"cmd": "cancel_all", "params": {}}
        if ticker:
            msg["params"]["ticker"] = ticker
        await self.send_order(ws, msg)

    def get_no_ticker(self, yes_ticker: str) -> str:
        return yes_ticker.replace("-YES", "-NO") if "-YES" in yes_ticker else yes_ticker + "-NO"

    async def on_fill(self, ws, fill_data: dict):
        f = fill_data['msg']['fill']
        ticker = f['ticker']
        side = f['side']
        price = f['price'] / 100.0
        size = f['size']

        net = self.positions.get(ticker, 0)
        net = net + size if side == "buy" else net - size
        self.positions[ticker] = net

        print(f"FILL {side.upper()} {size} {ticker} @ {price:.3f} → Net YES: {net}")

        # INSTANT ARBITRAGE HEDGE (the real money printer)
        if size >= 100 and "-YES" in ticker.upper():
            no_ticker = self.get_no_ticker(ticker)
            hedge_price = round(1.009 - price, 3)
            print(f"INSTANT HEDGE → SELL {size} {no_ticker} @ {hedge_price:.3f}")
            await self.place_limit(ws, no_ticker, "sell", hedge_price, size)

            # Emergency unwind after 7s if still exposed
            async def emergency():
                await asyncio.sleep(7)
                if self.positions.get(ticker, 0) != 0:
                    print(f"EMERGENCY FLATTEN {ticker}")
                    await self.place_limit(ws, ticker, "sell" if side == "buy" else "buy", 0, size)  # market order
            asyncio.create_task(emergency())

    async def on_orderbook_update(self, ws, ob: OrderBook):
        ticker = ob.ticker
        if "-YES" not in ticker.upper():
            return

        now = time.time()
        if ticker in self.last_quote and now - self.last_quote[ticker] < 0.22:
            return
        self.last_quote[ticker] = now

        bid = ob.best_bid()
        ask = ob.best_ask()
        spread = ask - bid
        micro = self.microprice(ob)

        size = 200
        if spread > 0.08:
            size = 800
        elif spread > 0.05:
            size = 400

        offset = 0.006
        if spread > 0.07:
            offset = 0.022
        elif spread > 0.04:
            offset = 0.013

        target_bid = round(micro - offset, 3)
        target_ask = round(micro + offset, 3)

        target_bid = min(target_bid, bid)
        target_ask = max(target_ask, ask)

        net = self.positions.get(ticker, 0)
        if abs(net) + size * 2 > 8000:
            return

        await self.cancel_all(ws, ticker)
        await asyncio.gather(
            self.place_limit(ws, ticker, "buy", target_bid, size),
            self.place_limit(ws, ticker, "sell", target_ask, size),
        )
        print(f"QUOTED {ticker} | {target_bid:.3f}–{target_ask:.3f} | Size: {size} | Spread: {spread:.3f}")