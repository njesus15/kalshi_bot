import requests
import pandas as pd
import time
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from typing import List, Dict, Optional

# ==================== YOUR KALSHI CREDENTIALS ====================
API_KEY = "b7433439-e616-45d5-aaa6-d7cb8c6218e5"  # Your API key (ID)
PRIVATE_KEY_FILE = "/Users/jesus/github/kalshi_bot/analysis/kalshi.pk"  # Path to your PEM private key file
# =================================================================

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

def load_private_key(file_path: str) -> rsa.RSAPrivateKey:
    """Load RSA private key from PEM file."""
    with open(file_path, "rb") as key_file:
        return serialization.load_pem_private_key(
            key_file.read(),
            password=None,  # Add password=b'passphrase' if encrypted
            backend=default_backend()
        )

def sign_pss_text(private_key: rsa.RSAPrivateKey, text: str) -> str:
    """Sign text with RSA-PSS (SHA256) and return base64 signature."""
    message = text.encode('utf-8')
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def sign_request(method: str, path: str, body: str = "") -> Dict[str, str]:
    """Generate Kalshi auth headers (RSA-PSS signing)."""
    private_key = load_private_key(PRIVATE_KEY_FILE)
    timestamp = str(int(time.time()))
    # Payload: timestamp + method.upper() + path (no query params, no body, no API key)
    payload = timestamp + method.upper() + path
    signature = sign_pss_text(private_key, payload)
    return {
        "KALSHI-ACCESS-KEY": API_KEY,
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
        "KALSHI-ACCESS-SIGNATURE": signature,
        "Content-Type": "application/json",
    }

def get_nba_series() -> List[str]:
    """Fetch all series and filter for NBA (public endpoint)."""
    r = requests.get(f"{BASE_URL}/series")
    if r.status_code != 200:
        print(f"Error fetching series: {r.status_code} {r.text[:200]}...")
        return []
    data = r.json()
    series_list = data.get("series", [])
    nba_series = [s["ticker"] for s in series_list if "nba" in s.get("title", "").lower()]
    print(f"Found NBA series tickers: {nba_series}")
    nba_series = ["KXNBAGAME"]
    return nba_series

def get_totals_markets(series_ticker: str, status: str = "settled") -> List[Dict]:
    """Fetch Over/Under markets from a series (public)."""
    markets = []
    cursor = None
    while True:
        params = {"series_ticker": series_ticker, "status": status, "limit": 500}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(f"{BASE_URL}/markets", params=params)
        if r.status_code != 200:
            print(f"Error for {series_ticker} ({status}): {r.status_code} {r.text[:200]}...")
            break
        data = r.json()
        batch = [m.get('ticker', '') for m in data.get("markets", [])]# if "TOT" in m.get("ticker", "").upper()]
        markets.extend(batch)
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(0.1)  # Rate limit
    return markets

def get_market_history(ticker: str) -> Optional[pd.DataFrame]:
    """Fetch price history (requires auth)."""
    path = f"/markets/{ticker}/history"
    headers = sign_request("GET", path)
    r = requests.get(f"{BASE_URL}{path}", headers=headers)
    if r.status_code == 401:
        print(f"401 Unauthorized for {ticker} → Invalid API key or private key file!")
        return None
    if r.status_code != 200:
        print(f"{ticker}: {r.status_code} {r.text[:200]}...")
        return None
    history = r.json().get("history", [])
    if not history:
        print(f"No history for {ticker} (market may be open)")
        return None
    df = pd.DataFrame(history)
    df["ticker"] = ticker
    df["timestamp"] = pd.to_datetime(df["created_time"], unit="s")
    cols = ["ticker", "timestamp", "yes_bid", "yes_ask", "last_price", "volume", "open_interest"]
    df = df[cols].copy()
    df[["yes_bid", "yes_ask", "last_price"]] /= 100.0  # Cents to dollars
    return df

def main():
    print("Fetching NBA series from Kalshi...\n")
    nba_series = get_nba_series()
    if not nba_series:
        print("No NBA series found — check API access or Kalshi's offerings.")
        return

    # Try settled markets first
    all_markets = []
    for series_ticker in nba_series:
        print(f"\nFetching settled totals from {series_ticker}...")
        series_markets = get_totals_markets(series_ticker, "settled")
        all_markets.extend(series_markets)

    if not all_markets:
        print("\nNo settled markets (early season — fetching open for preview)...")
        all_markets = []
        for series_ticker in nba_series:
            print(f"Fetching open totals from {series_ticker}...")
            series_markets = get_totals_markets(series_ticker, "open")
            all_markets.extend(series_markets)
        print(f"Found {len(all_markets)} open NBA totals markets (no history yet).")
        print("Re-run after games settle (e.g., after Dec 3) for full data.")
        #return  # No history for open

    print(f"\nTotal settled NBA totals markets: {len(all_markets)}")

    all_history = []
    print("\nFetching price histories...\n")
    for i, m in enumerate(all_markets):
        import pdb
        #pdb.set_trace()
        df = get_market_history(m)
        if df is not None and not df.empty:
            all_history.append(df)
        time.sleep(0.25)  # Rate limit

    if all_history:
        final_df = pd.concat(all_history, ignore_index=True)
        final_df = final_df.sort_values(["ticker", "timestamp"])
        filename = "kalshi_nba_totals_full_history.csv"
        final_df.to_csv(filename, index=False)
        print(f"\nSUCCESS! {len(final_df):,} price ticks from {len(all_history)} markets saved to {filename}")
        print("\nPreview (first 5 rows):")
        print(final_df.head().to_string(index=False))
    else:
        print("\nNo history retrieved. Check:")
        print("  • API key/private key (re-generate at kalshi.com/account/api).")
        print("  • Private key file path and format (PEM, unencrypted).")
        print("  • Settled markets exist (early Dec 2025 season).")

if __name__ == "__main__":
    main()