INSERT INTO imbalance
SELECT
    market,
    ts,
    (bid_size - ask_size) / NULLIF(bid_size + ask_size, 0) AS imbalance,
    CASE
        WHEN (bid_size - ask_size) / NULLIF(bid_size + ask_size, 0) > ? THEN 1
        WHEN (bid_size - ask_size) / NULLIF(bid_size + ask_size, 0) < -? THEN -1
        ELSE 0
    END AS signal
FROM read_parquet(?)
WHERE ts > ?
  AND ts <= ?
ON CONFLICT (market, ts) DO NOTHING;