import requests
import time
from datetime import datetime

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import base64

from kalshi_bot.core.data.market import Market


base_url = "https://api.elections.kalshi.com/"
endpoint = "/trade-api/v2/markets"
NBA_TICKER = 'KXNBAGAME'

def get_nba_sport_markets() -> list[str]:
    # Get all markets for the KXHIGHNY series
    markets_url = f"https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker={NBA_TICKER}&status=open"
    markets_response = requests.get(markets_url)
    markets_data = markets_response.json()
    markets = [parse_market(m) for m in markets_data["markets"]]
    return markets


# Your auth function (adapted from client.py)
def get_signed_headers(api_key: str, private_key_path: str, endpoint: str = "/trade-api/v2/markets") -> dict[str, str]:
    
    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
        
    timestamp = str(int(time.time() * 1000))  # Milliseconds!
    payload = timestamp + "GET" + "/trade-api/ws/v2"  # Exact payload for connect
    
    signature = private_key.sign(
        payload.encode('utf-8'),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH
        ),  # Changed from PSS to PKCS1v15
        hashes.SHA256()
    )
    
    return {
        "KALSHI-ACCESS-KEY": api_key,
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode('utf-8'),
    }


def parse_market(raw: dict) -> Market:
    def to_dt(ts: str) -> datetime:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))

    return Market(
        can_close_early=raw["can_close_early"],
        category=raw["category"],
        close_time=to_dt(raw["close_time"]),
        created_time=to_dt(raw["created_time"]),
        custom_strike=raw.get("custom_strike"),
        early_close_condition=raw.get("early_close_condition"),
        event_ticker=raw["event_ticker"],
        expected_expiration_time=to_dt(raw["expected_expiration_time"]),
        expiration_time=to_dt(raw["expiration_time"]),
        expiration_value=raw["expiration_value"],
        last_price=raw["last_price"],
        last_price_dollars=raw.get("last_price_dollars"),
        latest_expiration_time=to_dt(raw["latest_expiration_time"]) if raw.get("latest_expiration_time") else None,
        liquidity=raw["liquidity"],
        liquidity_dollars=raw.get("liquidity_dollars"),
        market_type=raw["market_type"],
        no_ask=raw["no_ask"],
        no_ask_dollars=raw.get("no_ask_dollars"),
        no_bid=raw["no_bid"],
        no_bid_dollars=raw.get("no_bid_dollars"),
        no_sub_title=raw.get("no_sub_title"),
        notional_value=raw.get("notional_value"),
        notional_value_dollars=raw.get("notional_value_dollars"),
        open_interest=raw["open_interest"],
        open_time=to_dt(raw["open_time"]),
        previous_price=raw["previous_price"],
        previous_price_dollars=raw.get("previous_price_dollars"),
        previous_yes_ask=raw["previous_yes_ask"],
        previous_yes_ask_dollars=raw.get("previous_yes_ask_dollars"),
        previous_yes_bid=raw["previous_yes_bid"],
        previous_yes_bid_dollars=raw.get("previous_yes_bid_dollars"),
        price_level_structure=raw.get("price_level_structure"),
        price_ranges=raw.get("price_ranges", []),
        response_price_units=raw["response_price_units"],
        result=raw["result"],
        risk_limit_cents=raw.get("risk_limit_cents"),
        rules_primary=raw["rules_primary"],
        rules_secondary=raw.get("rules_secondary"),
        settlement_timer_seconds=raw.get("settlement_timer_seconds"),
        status=raw["status"],
        strike_type=raw["strike_type"],
        subtitle=raw.get("subtitle"),
        tick_size=raw["tick_size"],
        ticker=raw["ticker"],
        title=raw["title"],
        volume=raw["volume"],
        volume_24h=raw["volume_24h"],
        yes_ask=raw["yes_ask"],
        yes_ask_dollars=raw.get("yes_ask_dollars"),
        yes_bid=raw["yes_bid"],
        yes_bid_dollars=raw.get("yes_bid_dollars"),
        yes_sub_title=raw.get("yes_sub_title"),
    )