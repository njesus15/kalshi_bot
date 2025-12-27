INSERT INTO imbalance
SELECT *
FROM (
    SELECT
        ticker,
        ts,
        (total_bid_vol - total_ask_vol) / NULLIF(total_bid_vol + total_ask_vol, 0) AS imbalance,
        CASE
            WHEN (total_bid_vol - total_ask_vol) / NULLIF(total_bid_vol + total_ask_vol, 0) > ? THEN 1
            WHEN (total_bid_vol - total_ask_vol) / NULLIF(total_bid_vol + total_ask_vol, 0) < -? THEN -1
            ELSE 0
        END AS signal
    FROM read_parquet(?)
    WHERE ts > now() - ? * INTERVAL '1 second'
) new_rows
WHERE NOT EXISTS (
    SELECT 1 FROM imbalance i
    WHERE i.ticker = new_rows.ticker
      AND i.ts = new_rows.ts
);