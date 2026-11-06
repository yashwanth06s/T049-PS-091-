class PublisherPayout:

    def __init__(self, publishers):
        self.publishers = {}

        for publisher in publishers:
            publisher_id = publisher["publisher_id"]

            self.publishers[publisher_id] = {
                "name": publisher["publisher_name"],
                "mtd_billed_before": float(
                    publisher["mtd_billed_before"]
                ),
                "rollover_in": float(
                    publisher["rollover_payout"]
                ),
                "new_billing": 0.0,
                "clawback": 0.0
            }

    def record_billing(self, publisher_id, amount):
        self.publishers[publisher_id]["new_billing"] += float(amount)

    def record_clawback(self, publisher_id, amount):
        self.publishers[publisher_id]["clawback"] += float(amount)

    def calculate_payout(self, publisher_id):

        publisher = self.publishers[publisher_id]

        mtd_billed = (
            publisher["mtd_billed_before"]
            + publisher["new_billing"]
        )

        # 70% only when monthly billing is greater than Rs 1 lakh
        share_pct = 70 if mtd_billed > 100000 else 60

        share_amount = (
            publisher["new_billing"] * share_pct / 100
        )

        payout_due = (
            share_amount
            + publisher["rollover_in"]
            - publisher["clawback"]
        )

        payout_due = max(0.0, payout_due)

        # Minimum payout threshold: Rs 5,000
        if payout_due < 5000:
            rolled_to_next = payout_due
            actual_payout = 0.0
        else:
            rolled_to_next = 0.0
            actual_payout = payout_due

        return {
            "publisher_id": publisher_id,
            "mtd_billed": round(mtd_billed, 2),
            "share_pct": share_pct,
            "share_amount": round(share_amount, 2),
            "clawback": round(publisher["clawback"], 2),
            "rollover_in": round(publisher["rollover_in"], 2),
            "payout_due": round(actual_payout, 2),
            "rolled_to_next": round(rolled_to_next, 2)
        }

    def generate_all_payouts(self):

        results = []

        for publisher_id in self.publishers:
            results.append(
                self.calculate_payout(publisher_id)
            )

        return results