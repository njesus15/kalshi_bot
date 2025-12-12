from dataclasses import dataclass
from typing import List, Dict, Tuple
import heapq
from functools import total_ordering

@dataclass(frozen=True)
class PriceLevel:
    # For bids: higher price = "smaller" in min-heap → we store negated price as sort key
    # For asks: lower price = "smaller" → we store price directly
    sort_key: float        # negated for bids, normal for asks
    price: float
    size: int
    timestamp: int = 0

    def __lt__(self, other):
        return self.sort_key < other.sort_key

    def __eq__(self, other):
        return self.sort_key == other.sort_key

    def __repr__(self):
        return f"({self.price:.4f}, {self.size})"


class OrderBook:
    def __init__(self, ticker: str):
        self.ticker = ticker

        # Min-heaps: bids (max-heap via negated price), asks (normal min-heap)
        self.bids: List[PriceLevel] = []   # max-heap simulation
        self.asks: List[PriceLevel] = []   # true min-heap

        # Fast price → size lookup
        self.bid_sizes: Dict[float, int] = {}
        self.ask_sizes: Dict[float, int] = {}

        # CACHED volumes — updated only when book changes
        self._total_bid_volume: int = 0
        self._total_ask_volume: int = 0
        self._volume_version: int = 0   # increments on every change

        self.last_update_ts: int = 0
        self.seq: int = 0

    def bid_volume(self) -> int:
        return self._total_bid_volume

    def ask_volume(self) -> int:
        return self._total_ask_volume

    def total_volume(self) -> int:
        return self._total_bid_volume + self._total_ask_volume
    
    def _add_bid(self, price: float, size: int, ts: int):
        old_size = self.bid_sizes.get(price, 0)
        size = max(0, size)

        # Update cached total
        self._total_bid_volume += size - old_size
        self._volume_version += 1

        if size <= 0:
            self.bid_sizes.pop(price, None)
            return
        self.bid_sizes[price] = size
        # Push with negated price to simulate max-heap
        heapq.heappush(self.bids, PriceLevel(-price, price, size, ts))

    def _add_ask(self, price: float, size: int, ts: int):
        old_size = self.bid_sizes.get(price, 0)
        size = max(0, size)

        # Update cached total
        self._total_ask_volume += size - old_size
        self._volume_version += 1

        if size <= 0:
            self.ask_sizes.pop(price, None)
            return
        self.ask_sizes[price] = size
        heapq.heappush(self.asks, PriceLevel(price, price, size, ts))

    def apply_snapshot(self, snapshot: dict, seq: int):
        """Apply full order book snapshot (yes/no format from Kalshi)"""
        self.bids.clear()
        self.asks.clear()
        self.bid_sizes.clear()
        self.ask_sizes.clear()
        self.seq = seq
        ts = snapshot.get("ts", 0)

        # YES bids = people buying YES → direct bids
        for price_cents, size in snapshot.get("yes", []):
            if size > 0:
                price = price_cents / 100.0
                self._add_bid(price, size, ts)

        # NO bids = people buying NO → equivalent to selling YES → becomes YES asks
        for price_cents, size in snapshot.get("no", []):
            import pdb
            pdb.set_trace()
            if size > 0:
                yes_price = 1.0 - (price_cents / 100.0)
                self._add_ask(yes_price, size, ts)

        self.last_update_ts = ts

    def apply_delta(self, update: dict, seq: int):
        """Apply incremental update: {price: int (cents), delta: int, side: 'yes'|'no', ts?: int}"""
        self.seq = seq
        price_cents = update["price"]
        delta = update["delta"]
        side = update["side"]  # "yes" or "no"
        ts = update.get("ts", self.last_update_ts)

        if side == "yes":
            price = price_cents / 100.0
            new_size = self.bid_sizes.get(price, 0) + delta
            self._add_bid(price, new_size, ts)
        else:  # side == "no"
            yes_price = 1.0 - (price_cents / 100.0)
            new_size = self.ask_sizes.get(yes_price, 0) + delta
            self._add_ask(yes_price, new_size, ts)

        self.last_update_ts = ts

    def _clean_heap(self, heap: List[PriceLevel], size_map: Dict[float, int]) -> None:
        """Remove stale entries from heap top"""
        while heap:
            top = heap[0]
            current_size = size_map.get(top.price, 0)
            if current_size == top.size and current_size > 0:
                break
            heapq.heappop(heap)

    def best_bid(self) -> float:
        self._clean_heap(self.bids, self.bid_sizes)
        return self.bids[0].price if self.bids else 0.0

    def best_ask(self) -> float:
        self._clean_heap(self.asks, self.ask_sizes)
        return self.asks[0].price if self.asks else 1.0

    def mid(self) -> float:
        bid, ask = self.best_bid(), self.best_ask()
        if bid <= 0 and ask >= 1: return 0.5
        if bid <= 0: return ask
        if ask >= 1: return bid
        return (bid + ask) / 2

    def top_n(self, n: int = 10) -> dict:
        self._clean_heap(self.bids, self.bid_sizes)
        self._clean_heap(self.asks, self.ask_sizes)

        # Extract up to n valid levels (since heap may have more, but we slice post-clean)
        valid_bids = [p for p in list(self.bids)[:n*2] if self.bid_sizes.get(p.price, 0) == p.size]  # Buffer for cleans
        valid_asks = [p for p in list(self.asks)[:n*2] if self.ask_sizes.get(p.price, 0) == p.size]

        top_bids = sorted(valid_bids, key=lambda x: -x.price)[:n]  # highest first
        top_asks = sorted(valid_asks, key=lambda x: x.price)[:n]   # lowest first

        return {
            "bids": [(p.price, p.size) for p in top_bids],
            "asks": [(p.price, p.size) for p in top_asks],
        }

    def __repr__(self):
        bid = self.best_bid()
        ask = self.best_ask()
        spread = ask - bid if bid > 0 and ask < 1 else 0.0
        return f"{self.ticker} | YES {bid:.4f} — {ask:.4f} (spread {spread:.4f})"