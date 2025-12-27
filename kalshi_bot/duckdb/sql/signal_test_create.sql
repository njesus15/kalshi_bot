CREATE TABLE IF NOT EXISTS imbalance (
    ticker VARCHAR,
    ts TIMESTAMP,
    imbalance DOUBLE,
    signal INTEGER
)