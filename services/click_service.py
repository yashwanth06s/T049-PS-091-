from collections import defaultdict
from datetime import timedelta
from decimal import Decimal


class ClickService:
    """
    Handles click processing, CPC billing, and Invalid Traffic (IVT) detection
    per BR-08, BR-10, and EC-06.
    """
    def __init__(self):
        self.clicks = []
        self.user_campaign_clicks = defaultdict(list)

    def process_click(self, click, campaign, publisher, budget_service, billing_service):
        user_id = click["user_id"]
        campaign_id = campaign.campaign_id
        publisher_id = publisher.publisher_id
        click_ts = click["click_ts"]
        hour = click_ts.hour

        # Check if daily spend < daily budget when click arrives (BR-08)
        # ONLY CPC campaigns are billed on click! CPM campaigns are billed per impression.
        current_daily_spend = budget_service.get_spend_today(campaign_id)
        budget = Decimal(str(campaign.daily_budget))
        cpc_bid = Decimal(str(campaign.max_bid))

        should_bill = (campaign.bid_type == "CPC") and (current_daily_spend < budget)
        billed_amount = Decimal("0.00")

        if should_bill:
            billed_amount = cpc_bid
            billing_service.charge_click(campaign.advertiser_id, publisher_id, billed_amount)
            budget_service.record_spend(campaign_id, hour, billed_amount)

        record = {
            "click_id": click["click_id"],
            "request_id": click["request_id"],
            "campaign_id": campaign_id,
            "publisher_id": publisher_id,
            "advertiser_id": campaign.advertiser_id,
            "user_id": user_id,
            "click_ts": click_ts,
            "hour": hour,
            "status": "VALID",
            "billed_amount": billed_amount,
            "reversed": False
        }

        self.clicks.append(record)
        key = (user_id, campaign_id)
        self.user_campaign_clicks[key].append(record)

        # BR-10 / EC-06: Check 10-minute rolling window for > 5 clicks (i.e. >= 6 clicks)
        history = self.user_campaign_clicks[key]
        n = len(history)
        if n >= 6:
            # Check sliding window
            for i in range(n):
                for j in range(i + 5, n):
                    if history[j]["click_ts"] - history[i]["click_ts"] <= timedelta(minutes=10):
                        # All clicks from i to j are marked INVALID
                        for k in range(i, j + 1):
                            target = history[k]
                            if target["status"] == "VALID" or not target["reversed"]:
                                target["status"] = "INVALID"
                                if target["billed_amount"] > Decimal("0.00") and not target["reversed"]:
                                    target["reversed"] = True
                                    # Refund advertiser & clawback publisher share
                                    billing_service.reverse_click(
                                        target["advertiser_id"],
                                        target["publisher_id"],
                                        target["billed_amount"]
                                    )
                                    budget_service.refund_spend(
                                        target["campaign_id"],
                                        target["hour"],
                                        target["billed_amount"]
                                    )
                                else:
                                    target["reversed"] = True

        return record

    def get_clicks_for_report(self):
        return [
            {
                "click_id": c["click_id"],
                "request_id": c["request_id"],
                "campaign_id": c["campaign_id"],
                "status": c["status"],
                "billed_amount": f"{c['billed_amount']:.2f}",
                "reversed": "true" if c["reversed"] else "false"
            }
            for c in self.clicks
        ]
