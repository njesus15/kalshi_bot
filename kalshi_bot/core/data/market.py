from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

@dataclass(frozen=True)
class Market:
    # === Required fields (no defaults) – must come first ===
    can_close_early: bool
    category: str
    close_time: datetime
    created_time: datetime
    event_ticker: str
    expected_expiration_time: datetime
    expiration_time: datetime
    expiration_value: str
    last_price: int
    market_type: str
    no_ask: int
    no_bid: int
    open_interest: int
    volume: int
    volume_24h: int
    open_time: datetime
    previous_price: int
    previous_yes_ask: int
    previous_yes_bid: int
    rules_primary: str
    status: str
    strike_type: str
    tick_size: int
    ticker: str
    title: str
    yes_ask: int
    yes_bid: int

    # === Optional / defaulted fields – all go after ===
    custom_strike: Optional[Dict[str, str]] = None
    early_close_condition: Optional[str] = None
    latest_expiration_time: Optional[datetime] = None
    liquidity: int = 0
    liquidity_dollars: Optional[str] = None
    no_ask_dollars: Optional[str] = None
    no_bid_dollars: Optional[str] = None
    no_sub_title: Optional[str] = None
    notional_value: Optional[int] = None
    notional_value_dollars: Optional[str] = None
    previous_price_dollars: Optional[str] = None
    previous_yes_ask_dollars: Optional[str] = None
    previous_yes_bid_dollars: Optional[str] = None
    price_level_structure: Optional[str] = None
    price_ranges: List[Dict] = field(default_factory=list)
    response_price_units: str = "per_share"  # almost always this
    result: str = ""  # empty until settled
    risk_limit_cents: Optional[int] = None
    rules_secondary: Optional[str] = None
    settlement_timer_seconds: Optional[int] = None
    subtitle: Optional[str] = None
    yes_ask_dollars: Optional[str] = None
    yes_bid_dollars: Optional[str] = None
    yes_sub_title: Optional[str] = None
    last_price_dollars: Optional[str] = None

    # === Helpful computed properties ===
    @property
    def yes_bid_decimal(self) -> Decimal:
        return Decimal(self.yes_bid) / 100

    @property
    def yes_ask_decimal(self) -> Decimal:
        return Decimal(self.yes_ask) / 100

    @property
    def last_price_decimal(self) -> Decimal:
        return Decimal(self.last_price) / 100

    @property
    def previous_price_decimal(self) -> Decimal:
        return Decimal(self.previous_price) / 100

    @property
    def spread_cents(self) -> int:
        return self.yes_ask - self.yes_bid

    @property
    def spread_bp(self) -> Decimal:
        return Decimal(self.spread_cents) / 100