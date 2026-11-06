class WalletManager:

    def __init__(self, advertisers):
        self.advertisers = {}

        for advertiser in advertisers:
            advertiser_id = advertiser["advertiser_id"]

            self.advertisers[advertiser_id] = {
                "account_type": advertiser["account_type"],
                "balance": float(advertiser["wallet_balance"]),
                "credit_limit": float(advertiser["credit_limit"]),
                "suspended": False
            }

    def can_afford(self, advertiser_id, required_amount):

        account = self.advertisers[advertiser_id]

        if account["suspended"]:
            return False

        if account["account_type"] == "PREPAID":
            return account["balance"] >= required_amount

        return True

    def charge(self, advertiser_id, amount):

        account = self.advertisers[advertiser_id]

        if account["suspended"]:
            return False

        amount = round(float(amount), 2)

        if account["account_type"] == "PREPAID":

            account["balance"] = round(
                account["balance"] - amount, 2
            )

        else:

            account["balance"] = round(
                account["balance"] - amount, 2
            )

            if account["balance"] < -account["credit_limit"]:
                account["suspended"] = True

        return True

    def refund(self, advertiser_id, amount):

        account = self.advertisers[advertiser_id]

        account["balance"] = round(
            account["balance"] + float(amount), 2
        )

    def get_balance(self, advertiser_id):

        return self.advertisers[advertiser_id]["balance"]

    def is_suspended(self, advertiser_id):

        return self.advertisers[advertiser_id]["suspended"]