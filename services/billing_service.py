from decimal import Decimal


class BillingService:
    """
    Manages billing, wallet debits, credit account limits, IVT reversals,
    and publisher payouts per BR-08, BR-09, BR-10, BR-11, EC-06, EC-07, and EC-08.
    """
    def __init__(self, advertisers, publishers):
        self.advertisers = advertisers
        self.publishers = publishers

        # Month-to-date billed per publisher (starts with mtd_billed_before)
        self.publisher_mtd_billed = {
            pid: Decimal(str(p.monthly_billed_amount))
            for pid, p in publishers.items()
        }
        self.publisher_new_billed = {
            pid: Decimal("0.00")
            for pid in publishers
        }
        self.publisher_clawbacks = {
            pid: Decimal("0.00")
            for pid in publishers
        }
        self.transactions = []

    def get_advertiser(self, advertiser_id):
        return self.advertisers[advertiser_id]

    def can_afford(self, advertiser_id, amount):
        adv = self.get_advertiser(advertiser_id)
        if adv.suspended:
            return False
        if adv.account_type == "PREPAID":
            return Decimal(str(adv.wallet_balance)) >= Decimal(str(amount))
        # CREDIT accounts can bid as long as they are not suspended
        return True

    def charge_impression(self, advertiser_id, publisher_id, clearing_cpm):
        """
        BR-08 / EC-08: Charge CPM impression at clearing_cpm / 1000.
        Credit accounts: a charge taking balance below -credit_limit stands and suspends the advertiser.
        """
        amount = Decimal(str(clearing_cpm)) / Decimal("1000")
        adv = self.get_advertiser(advertiser_id)

        # Debit wallet / credit
        current_bal = Decimal(str(adv.wallet_balance))
        new_bal = current_bal - amount
        adv.wallet_balance = float(new_bal)

        # BR-09 / EC-08: Credit advertiser suspended if balance drops below -credit_limit
        credit_limit = Decimal(str(adv.credit_limit))
        if adv.account_type == "CREDIT" and new_bal < -credit_limit:
            adv.suspended = True

        self.publisher_mtd_billed[publisher_id] += amount
        self.publisher_new_billed[publisher_id] += amount

        txn = {
            "type": "IMPRESSION",
            "advertiser_id": advertiser_id,
            "publisher_id": publisher_id,
            "amount": amount,
            "reversed": False
        }
        self.transactions.append(txn)
        return amount

    def charge_click(self, advertiser_id, publisher_id, cpc_bid):
        """
        BR-08: Charge CPC click at campaign max_bid.
        """
        amount = Decimal(str(cpc_bid))
        adv = self.get_advertiser(advertiser_id)

        current_bal = Decimal(str(adv.wallet_balance))
        new_bal = current_bal - amount
        adv.wallet_balance = float(new_bal)

        credit_limit = Decimal(str(adv.credit_limit))
        if adv.account_type == "CREDIT" and new_bal < -credit_limit:
            adv.suspended = True

        self.publisher_mtd_billed[publisher_id] += amount
        self.publisher_new_billed[publisher_id] += amount

        txn = {
            "type": "CLICK",
            "advertiser_id": advertiser_id,
            "publisher_id": publisher_id,
            "amount": amount,
            "reversed": False
        }
        self.transactions.append(txn)
        return amount

    def reverse_click(self, advertiser_id, publisher_id, amount):
        """
        BR-10 / EC-06: Reverse billing on invalid clicks.
        Refunds advertiser and registers publisher clawback.
        """
        amt = Decimal(str(amount))
        adv = self.get_advertiser(advertiser_id)

        # Refund advertiser
        adv.wallet_balance = float(Decimal(str(adv.wallet_balance)) + amt)

        # Publisher rev share rate (60% or 70%)
        pub = self.publishers[publisher_id]
        total_billed = self.publisher_mtd_billed[publisher_id]
        share_pct = Decimal("70") if total_billed > Decimal("100000.00") else Decimal("60")

        # Claw back the publisher's share
        clawback_amount = amt * share_pct / Decimal("100.0")
        self.publisher_clawbacks[publisher_id] += clawback_amount

    def get_publisher_payout(self, publisher_id):
        """
        BR-11 / EC-07: Compute publisher payout for the month.
        - 70% rev share if month billing > Rs 1,00,000; else 60%
        - Payouts < Rs 5,000 roll to next month.
        """
        pub = self.publishers[publisher_id]
        mtd_billed = self.publisher_mtd_billed[publisher_id]

        share_pct = 70 if mtd_billed > Decimal("100000.00") else 60
        share_amount = mtd_billed * Decimal(str(share_pct)) / Decimal("100.0")

        clawback = self.publisher_clawbacks[publisher_id]
        rollover_in = Decimal(str(pub.rollover_payout))

        total_due = share_amount + rollover_in - clawback
        total_due = max(Decimal("0.00"), total_due)

        if total_due < Decimal("5000.00"):
            actual_payout = Decimal("0.00")
            rolled_to_next = total_due
        else:
            actual_payout = total_due
            rolled_to_next = Decimal("0.00")

        return {
            "publisher_id": publisher_id,
            "mtd_billed": f"{mtd_billed:.2f}",
            "share_pct": share_pct,
            "share_amount": f"{share_amount:.2f}",
            "clawback": f"{clawback:.2f}",
            "rollover_in": f"{rollover_in:.2f}",
            "payout_due": f"{actual_payout:.2f}",
            "rolled_to_next": f"{rolled_to_next:.2f}"
        }

    def generate_all_publisher_payouts(self):
        return [
            self.get_publisher_payout(pid)
            for pid in sorted(self.publishers.keys())
        ]
