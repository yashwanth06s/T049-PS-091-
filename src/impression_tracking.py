from collections import defaultdict


class ImpressionTracker:

    def __init__(self):
        self.impressions = defaultdict(int)
        self.daily_impressions = defaultdict(int)
        self.valid_clicks = defaultdict(int)
        self.invalid_clicks = defaultdict(int)

    def record_impression(self, campaign_id, date):
        self.impressions[campaign_id] += 1

        key = (campaign_id, date)
        self.daily_impressions[key] += 1

    def record_valid_click(self, campaign_id, date):
        key = (campaign_id, date)
        self.valid_clicks[key] += 1

    def record_invalid_click(self, campaign_id, date):
        key = (campaign_id, date)
        self.invalid_clicks[key] += 1

    def get_impressions(self, campaign_id, date=None):
        if date is None:
            return self.impressions[campaign_id]

        return self.daily_impressions[(campaign_id, date)]

    def get_valid_clicks(self, campaign_id, date):
        return self.valid_clicks[(campaign_id, date)]

    def get_invalid_clicks(self, campaign_id, date):
        return self.invalid_clicks[(campaign_id, date)]

    def get_total_clicks(self, campaign_id, date):
        return (
            self.get_valid_clicks(campaign_id, date)
            + self.get_invalid_clicks(campaign_id, date)
        )