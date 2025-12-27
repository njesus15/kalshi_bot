CREATE TABLE IF NOT EXISTS imbalance (
    market    VARCHAR,
    ts        TIMESTAMP,
    imbalance DOUBLE,
    signal    INTEGER,
    PRIMARY KEY (market, ts)
);