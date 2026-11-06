from decimal import Decimal


class BudgetService:
    """
    Manages campaign budget pacing and throttling per BR-06, BR-07, and EC-04.
    """
    def __init__(self, traffic_profile):
        self.traffic_profile = {
            int(h): Decimal(str(p))
            for h, p in traffic_profile.items()
        }
        self.daily_spend = {}
        self.hourly_spend = {}

    def open_day(self):
        self.daily_spend.clear()
        self.hourly_spend.clear()

    def get_spend_today(self, campaign_id):
        return self.daily_spend.get(campaign_id, Decimal("0.00"))

    def get_hourly_spend(self, campaign_id, hour):
        return self.hourly_spend.get((campaign_id, int(hour)), Decimal("0.00"))

    def get_scheduled_budget(self, campaign, hour):
        budget = Decimal(str(campaign.daily_budget))
        scheduled_pct = sum(
            (self.traffic_profile.get(h, Decimal("0.00")) for h in range(int(hour) + 1)),
            Decimal("0.00")
        )
        return budget * scheduled_pct / Decimal("100.0")

    def get_pacing_status(self, campaign, hour):
        spend = self.get_spend_today(campaign.campaign_id)
        scheduled = self.get_scheduled_budget(campaign, hour)

        # OVER_PACE if spend >= 120% of cumulative scheduled budget
        if spend >= scheduled * Decimal("1.20"):
            return "OVER_PACE"
        # UNDER_PACE if spend < 100% of cumulative scheduled budget
        if spend < scheduled:
            return "UNDER_PACE"
        return "ON_PACE"

    def can_bid(self, campaign, hour, request_sequence):
        """
        Determines if campaign can participate in auction based on pacing & throttling.
        Returns: (can_participate: bool, pacing_status: str, sit_out_reason: str)
        """
        status = self.get_pacing_status(campaign, hour)
        campaign_id = campaign.campaign_id

        # BR-07 / EC-04: When OVER_PACE, participates only in every 2nd eligible request (even sequence numbers)
        if status == "OVER_PACE":
            if int(request_sequence) % 2 != 0:
                return False, status, "Throttled: over pace on odd request sequence"
            return True, status, ""

        # BR-06: When UNDER_PACE, throttle lifted, but capped at 150% of current hour bucket
        if status == "UNDER_PACE":
            budget = Decimal(str(campaign.daily_budget))
            hour_bucket = budget * self.traffic_profile.get(int(hour), Decimal("0.00")) / Decimal("100.0")
            spent_hour = self.get_hourly_spend(campaign_id, hour)
            if spent_hour >= hour_bucket * Decimal("1.50"):
                return False, status, "Catch-up hourly spend cap (150%) reached"
            return True, status, ""

        return True, status, ""

    def record_spend(self, campaign_id, hour, amount):
        amt = Decimal(str(amount))
        self.daily_spend[campaign_id] = self.get_spend_today(campaign_id) + amt
        key = (campaign_id, int(hour))
        self.hourly_spend[key] = self.get_hourly_spend(campaign_id, hour) + amt

    def refund_spend(self, campaign_id, hour, amount):
        amt = Decimal(str(amount))
        current_daily = self.get_spend_today(campaign_id)
        self.daily_spend[campaign_id] = max(Decimal("0.00"), current_daily - amt)
        key = (campaign_id, int(hour))
        current_hourly = self.get_hourly_spend(campaign_id, hour)
        self.hourly_spend[key] = max(Decimal("0.00"), current_hourly - amt)
