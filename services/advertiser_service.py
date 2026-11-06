class AdvertiserService:
    def __init__(self):
        self.advertisers = {}

    def add_advertiser(self, advertiser):
        if advertiser.advertiser_id in self.advertisers:
            raise ValueError("Advertiser already exists")

        self.advertisers[advertiser.advertiser_id] = advertiser
        return advertiser

    def get_advertiser(self, advertiser_id):
        if advertiser_id not in self.advertisers:
            raise ValueError("Advertiser not found")

        return self.advertisers[advertiser_id]

    def can_spend(self, advertiser_id, amount):
        advertiser = self.get_advertiser(advertiser_id)

        if advertiser.suspended:
            return False

        if advertiser.account_type == "PREPAID":
            return advertiser.wallet_balance >= amount

        return True

    def charge(self, advertiser_id, amount):
        advertiser = self.get_advertiser(advertiser_id)

        if amount < 0:
            raise ValueError("Charge cannot be negative")

        if advertiser.suspended:
            return False

        if advertiser.account_type == "PREPAID":
            if advertiser.wallet_balance < amount:
                return False

        advertiser.wallet_balance -= amount

        if (
            advertiser.account_type == "CREDIT"
            and advertiser.wallet_balance < -advertiser.credit_limit
        ):
            advertiser.suspended = True

        return True