class BudgetPacing:

    def __init__(self, daily_budget, traffic_profile):
        self.daily_budget = float(daily_budget)

        self.hourly_budgets = {
            int(row["hour"]): (
                self.daily_budget *
                float(row["pct_of_daily_budget"]) / 100
            )
            for row in traffic_profile
        }

        self.spend_today = 0.0
        self.hourly_spend = {}

    def reset(self):
        self.spend_today = 0.0
        self.hourly_spend = {}

    def get_scheduled_budget(self, hour):
        return sum(
            self.hourly_budgets.get(h, 0.0)
            for h in range(0, hour + 1)
        )

    def get_pacing_status(self, hour):

        scheduled = self.get_scheduled_budget(hour)

        if scheduled <= 0:
            return "UNDER_PACE"

        if self.spend_today >= scheduled * 1.20:
            return "OVER_PACE"

        if self.spend_today < scheduled:
            return "UNDER_PACE"

        return "ON_PACE"

    def can_spend(self, amount, hour, request_sequence):

        amount = float(amount)
        hour = int(hour)
        request_sequence = int(request_sequence)

        if self.spend_today + amount > self.daily_budget:
            return False

        status = self.get_pacing_status(hour)

        if status == "OVER_PACE":
            if request_sequence % 2 != 0:
                return False

        if status == "UNDER_PACE":
            hour_budget = self.hourly_budgets.get(hour, 0.0)
            current_hour_spend = self.hourly_spend.get(hour, 0.0)

            if current_hour_spend + amount > hour_budget * 1.50:
                return False

        return True

    def record_spend(self, amount, hour):

        amount = float(amount)
        hour = int(hour)

        self.spend_today += amount

        self.hourly_spend[hour] = (
            self.hourly_spend.get(hour, 0.0) + amount
        )

    def get_spend(self):
        return round(self.spend_today, 2)

    def get_status(self, hour):
        return self.get_pacing_status(hour)