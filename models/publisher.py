from dataclasses import dataclass


@dataclass
class Publisher:
    publisher_id: str
    name: str
    floor_price: float
    monthly_billed_amount: float
    rollover_payout: float = 0.0

    def __post_init__(self):
        if not self.publisher_id.strip():
            raise ValueError("Publisher ID cannot be empty")

        if not self.name.strip():
            raise ValueError("Publisher name cannot be empty")

        if self.floor_price < 0:
            raise ValueError("Floor price cannot be negative")

        if self.monthly_billed_amount < 0:
            raise ValueError("Monthly billed amount cannot be negative")

        if self.rollover_payout < 0:
            raise ValueError("Rollover payout cannot be negative")

    @property
    def revenue_share(self):
        return 70 if self.monthly_billed_amount > 100000 else 60