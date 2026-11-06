from dataclasses import dataclass


@dataclass
class Advertiser:
    advertiser_id: str
    name: str
    account_type: str
    wallet_balance: float
    credit_limit: float
    suspended: bool = False

    def __post_init__(self):
        if not self.advertiser_id.strip():
            raise ValueError("Advertiser ID cannot be empty")

        if not self.name.strip():
            raise ValueError("Advertiser name cannot be empty")

        self.account_type = self.account_type.upper()

        if self.account_type not in ("PREPAID", "CREDIT"):
            raise ValueError("Account type must be PREPAID or CREDIT")

        if self.credit_limit < 0:
            raise ValueError("Credit limit cannot be negative")

        if self.account_type == "PREPAID" and self.wallet_balance < 0:
            raise ValueError("Prepaid wallet cannot be negative")

        if self.account_type == "CREDIT" and self.wallet_balance < -self.credit_limit:
            raise ValueError("Balance exceeds credit limit")