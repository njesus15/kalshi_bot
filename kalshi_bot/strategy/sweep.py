import json

from kalshi_bot.core.data.order_book import OrderBook

class Sweep:
    def __init__(self):
        self.positions = {}
        self.last_ask = {}
        self.last_bid = {}
        self.buy_size = 800
        self.max_position = 6000

    async def on_orderbook_update(self, ob: OrderBook):
        ticker = ob.ticker
        bid = ob.best_bid()      # This IS the YES price
        ask = ob.best_ask()      # This is the NO price (don't use it)

        prev_bid = self.last_bid.get(ticker, bid)

        # Only trigger when YES is near-certain (>95.5%)
        if bid < 0.955:
            self.last_bid[ticker] = bid
            return

        # Detect panic sell: YES bid/ask crashes 3+ cents
        if ask < prev_bid - 0.029 or bid < 0.93:
            print(f"PANIC DIP {ticker} | YES {bid:.3f} → Ask {ask:.3f}")
            #await ws.send(json.dumps({
            #    "cmd": "create_order",
            #    "params": {
            #        "ticker": ticker,
            #        "side": "buy",
            #        "type": "market",
            #        "size": self.buy_size
            #    }
            #}))
            print(f"MARKET BUY {self.buy_size} YES @ ~{ask:.3f}")

        self.last_bid[ticker] = bid