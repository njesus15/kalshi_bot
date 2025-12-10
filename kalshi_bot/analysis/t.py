import requests
import pandas as pd
import time
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from typing import List, Dict, Optional

# ==============================================================
# PASTE YOUR REAL KALSHI CREDENTIALS BELOW (from kalshi.com/account/api)
# ==============================================================
API_KEY = "ak_your_real_key_here"          # ← starts with "ak_"
API_SECRET = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...
your full private key here (keep all lines, including BEGIN/END)
-----END PRIVATE KEY-----"""
# ==============================================================

# Updated base URL for 2025 migration
BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

def sign_request(method: str, path: str, body: str = "") -> Dict[str, str]:
    """Generate RSA signature for Kalshi auth (unchanged)."""
    timestamp = str(int(time.time()))
    payload = timestamp + API_KEY + method.upper() + path + body
    private_key = serialization.load_pem_private_key(API_SECRET.encode(), password=None)
    signature = private_key.sign(payload.encode(), padding.PKCS1v15(), hashes.SHA256())
    return {
        "KALSHI-API-KEY": API_KEY,
        "KALSHI-TIMESTAMP": timestamp,
        "KALSHI-SIGNATURE": base64.b64encode(signature).decode(),
        "Content-Type": "application/json",
    }

def get_nba_series() -> List[str]:
    """Fetch all series and filter for NBA ones (public endpoint)."""
    r = requests.get(f"{BASE_URL}/series")
    if r.status_code != 200:
        print(f"Error fetching series: {r.status_code} {r.text[:200]}...")
        return []
    data = r.json()
    series = data.get("series", [])
    nba_series = [s["ticker"] for s in series if "nba" in s.get("title", "").lower()]
    print(f"Found NBA series: {nba_series}")
    return nba_series

def get_totals_markets(series_ticker: str, status: str = "settled") -> List[Dict]:
    """Fetch totals markets from a series (public)."""
    markets = []
    cursor = None
    while True:
        params = {
            "series_ticker": series_ticker,
            "status": status,
            "limit": 500
        }
        if cursor:
            params["cursor"] = cursor

        r = requests.get(f"{BASE_URL}/markets", params=params)
        if r.status_code != 200:
            print(f"Error fetching markets for {series_ticker}: {r.status_code} {r.text[:200]}...")
            break
        data = r.json()
        batch = [m for m in data.get("markets", []) if "OVER" in m.get("title", "").upper() or "UNDER" in m.get("title", "").upper()]
        markets.extend(batch)
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(0.1)
    return markets

def get_market_history(ticker: str) -> Optional[pd.DataFrame]:
    """Fetch full price history (requires auth)."""
    path = f"/markets/{ticker}/history"
    headers = sign_request("GET", path)
    r = requests.get(f"{BASE_URL}{path}", headers=headers)

    if r.status_code == 401:
        print(f"401 Unauthorized on {ticker} → Check API_KEY and private key (must be full block)!")
        return None
    if r.status_code != 200:
        print(f"{ticker}: {r.status_code} {r.text[:200]}...")
        return None

    history = r.json().get("history", [])
    if not history:
        print(f"No history for {ticker} (likely open market)")
        return None

    df = pd.DataFrame(history)
    df["ticker"] = ticker
    df["timestamp"] = pd.to_datetime(df["created_time"], unit="s")
    cols = ["ticker", "timestamp", "yes_bid", "yes_ask", "last_price", "volume", "open_interest"]
    df = df[cols].copy()
    df[["yes_bid", "yes_ask", "last_price"]] /= 100.0  # Convert cents to dollars
    return df

def main():
    print("Fetching NBA series from Kalshi...\n")
    nba_series = get_nba_series()
    if not nba_series:
        print("No NBA series found. Check API access or Kalshi's current offerings.")
        return

    # Try settled first
    all_markets = []
    for series_ticker in nba_series:
        print(f"\nFetching settled totals from series {series_ticker}...")
        series_markets = get_totals_markets(series_ticker, "settled")
        all_markets.extend(series_markets)

    if not all_markets:
        print("\nNo settled markets (NBA season just started — try open markets for preview)...")
        all_markets = []
        for series_ticker in nba_series:
            print(f"Fetching open totals from series {series_ticker}...")
            series_markets = get_totals_markets(series_ticker, "open")
            all_markets.extend(series_markets)
        print(f"Found {len(all_markets)} open NBA totals markets (no history available yet).")
        print("Run again after some games settle for full historical prices.")
        return  # No history for open markets

    print(f"\nTotal settled NBA totals markets found: {len(all_markets)}")

    all_history = []
    print("\nFetching price histories...\n")
    for i, market in enumerate(all_markets, 1):
        ticker = market["ticker"]
        title = market.get("title_short") or market.get("title", "")
        print(f"[{i}/{len(all_markets)}] {ticker} → {title}")
        df = get_market_history(ticker)
        if df is not None and not df.empty:
            all_history.append(df)
        time.sleep(0.25)

    if all_history:
        final_df = pd.concat(all_history, ignore_index=True)
        final_df = final_df.sort_values(["ticker", "timestamp"])
        filename = "kalshi_nba_totals_full_history.csv"
        final_df.to_csv(filename, index=False)
        print(f"\nSUCCESS! {len(final_df):,} price ticks from {len(all_history)} markets saved to {filename}")
        print("\nPreview (first 5 rows):")
        print(final_df.head().to_string(index=False))
    else:
        print("\nNo price history retrieved. Common causes:")
        print("  • Invalid API keys (re-generate at kalshi.com/account/api).")
        print("  • No settled markets with history (early season — check back after Dec 3 games).")
        print("  • Rate limit hit — wait 1 min and retry.")

if __name__ == "__main__":
    if "ak_" not in API_KEY or "PRIVATE KEY" not in API_SECRET:
        print("STOP: Edit main.py and paste your real Kalshi API key + full private key block!")
        print("Get them at https://kalshi.com/account/api — private key is multiline, keep BEGIN/END.")
    else:
        main()