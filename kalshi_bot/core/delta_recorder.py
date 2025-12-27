# kalshi_bot/core/delta_recorder.py
import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any

import pyarrow as pa
import pyarrow.parquet as pq

from kalshi_bot.core.data.order_book import OrderBook


# Fixed schema — all fields defined once, works forever
SCHEMA = pa.schema([
    ("ts", pa.timestamp('ms')),
    ("date", pa.date32()),
    ("ticker", pa.string()),
    ("seq", pa.int64()),
    ("msg_type", pa.string()),
    ("price_cents", pa.int32()),
    ("price", pa.float64()),
    ("delta", pa.int64()),
    ("side", pa.string()),
    ("best_bid", pa.float64()),
    ("best_ask", pa.float64()),
    ("mid", pa.float64()),
    ("spread", pa.float64()),
    ("total_bid_vol", pa.int64()),
    ("total_ask_vol", pa.int64()),
    ("top_bids_and_asks", pa.string()),  # JSON string
])


class DeltaRecorder:
    def __init__(self, ticker: str, max_buffer: int = 25_000):
        self.ticker = ticker
        self.max_buffer = 10
        self.buffer: list[Dict[str, Any]] = []
        self.queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=100_000)

        self.base_path = f"kalshi_deltas/{ticker}"
        os.makedirs(self.base_path, exist_ok=True)

        # Start the background flusher immediately
        self._flush_task = None

    async def start(self):
        """Call this once the event loop is running."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._flush_worker())

    async def _flush_worker(self):
        """Background task — does ALL disk I/O. Runs forever."""
        while True:
            # Wait for at least one item (or timeout to force periodic flush)
            try:
                item = await asyncio.wait_for(self.queue.get(), timeout=10.0)
            except asyncio.TimeoutError:
                item = None  # will trigger flush if buffer has data

            if item is not None:
                self.buffer.append(item)

            # Drain as much as possible without blocking
            while len(self.buffer) < self.max_buffer:
                try:
                    item2 = self.queue.get_nowait()
                    self.buffer.append(item2)
                except asyncio.QueueEmpty:
                    break

            # Flush when buffer full OR on timeout and has data
            if len(self.buffer) >= self.max_buffer or (item is None and self.buffer):
                if self.buffer:
                    # Offload heavy I/O to thread pool
                    await asyncio.to_thread(self._write_parquet_batch, self.buffer.copy())
                    self.buffer.clear()

            # Mark everything we consumed as done
            if item is not None:
                self.queue.task_done()
            # Mark everything we drained with get_nowait()
            drained = 0
            while True:
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                    drained += 1
                except asyncio.QueueEmpty:
                    break

    def _write_parquet_batch(self, records: list[dict]):
        if not records:
            return

        # CRITICAL: ALWAYS add date column BEFORE creating table
        for r in records:
            r["date"] = datetime.utcfromtimestamp(r["ts"] / 1000.0).date()

        # FORCE the schema — this time — no inference allowed
        table = pa.Table.from_pylist(records, schema=SCHEMA)

        today = datetime.utcnow().strftime("%Y-%m-%d")
        file_path = os.path.join(self.base_path, f"{today}.parquet")

        if os.path.exists(file_path):
            try:
                existing = pq.read_table(file_path, schema=SCHEMA)  # ← force same schema
                table = pa.concat_tables([existing, table], promote=True)
            except Exception as e:
                print(f"[WARN] Corrupted Parquet {file_path}: {e}. Overwriting with fresh file.")
        
        # Write with EXACT schema
        print(f"Writing {len(records)} record(s) for {self.ticker} at {datetime.utcnow()}")
        print(file_path)
        pq.write_table(
            table,
            file_path,
            compression="zstd",           # keep zstd — it's still the best
            compression_level=3,          # 1–3 is plenty fast and avoids the hang
            use_dictionary=False,         # ← THIS IS THE KEY — disables the buggy path
            write_statistics=False,   # ← KEY: Avoids metadata threading deadlock
            flavor="default",         # ← KEY: Skip "spark" (it's the culprit)
        )
    # ————————————————————————
    # These are called from the hot path — super fast
    # ————————————————————————
    async def log_delta(self, delta_msg: dict, seq: int, bbid: float, bask: float, mid: float, bid_vol: float, ask_vol: float, top_n):

        dt = datetime.fromisoformat(delta_msg['ts'].replace("Z", "+00:00"))
        record: Dict[str, Any] = {
            "ts": int(dt.timestamp() * 1000),
            "ticker": self.ticker,
            "seq": seq,
            "msg_type": "delta",
            "price_cents": delta_msg.get("price"),
            "price": (delta_msg.get("price", 0) / 100.0) if delta_msg.get("price") is not None else None,
            "delta": delta_msg.get("delta"),
            "side": delta_msg.get("side"),
            "best_bid": bbid if bbid > 0 else None,
            "best_ask": bask if bask < 1 else None,
            "mid": mid,
            "spread": (bask - bbid) if bbid > 0 and bask < 1 else None,
            "total_bid_vol": bid_vol,
            "total_ask_vol": ask_vol,
            "top_bids_and_asks": json.dumps(top_n),
        }

        try:
            self.queue.put_nowait(record)
        except asyncio.QueueFull:
            # Don't lose data — wait briefly
            await self.queue.put(record)

    async def log_snapshot(self, seq: int, bbid: float, bask: float, mid: float, bid_vol: float, ask_vol: float, top_n):
        record: Dict[str, Any] = {
            "ts": int(datetime.utcnow().timestamp() * 1000),
            "ticker": self.ticker,
            "seq": seq,
            "msg_type": "orderbook_snapshot",
            "price_cents": None,
            "price": None,
            "delta": None,
            "side": None,
            "best_bid": bbid if bbid > 0 else None,
            "best_ask": bask if bask < 1 else None,
            "mid": mid,
            "spread": (bask - bbid) if bbid > 0 and bask < 1 else None,
            "total_bid_vol": bid_vol,
            "total_ask_vol": ask_vol,
            "top_bids_and_asks": json.dumps(top_n),
        }

        try:
            self.queue.put_nowait(record)
        except asyncio.QueueFull:
            await self.queue.put(record)

    async def flush(self):
        """Call at shutdown to write everything left."""
        # Drain queue into buffer
        while not self.queue.empty():
            try:
                item = self.queue.get_nowait()
                self.buffer.append(item)
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break

        if self.buffer:
            await asyncio.to_thread(self._write_parquet_batch, self.buffer.copy())
            self.buffer.clear()