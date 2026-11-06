from dataclasses import dataclass
from datetime import date


@dataclass
class Campaign:
    campaign_id: str
    advertiser_id: str
    flight_start: date
    flight_end: date
    daily_budget: float
    bid_type: str
    max_bid: float
    target_geos: list
    target_devices: list
    target_categories: list
    freq_cap_day: int
    freq_cap_hour: int

    def __post_init__(self):
        if self.flight_start > self.flight_end:
            raise ValueError("Invalid campaign flight dates")

        if self.daily_budget <= 0 or self.max_bid <= 0:
            raise ValueError("Budget and bid must be positive")

        self.bid_type = self.bid_type.upper()

        if self.bid_type not in ("CPM", "CPC"):
            raise ValueError("Bid type must be CPM or CPC")

        if self.freq_cap_day <= 0 or self.freq_cap_hour <= 0:
            raise ValueError("Frequency caps must be positive")