from collections import defaultdict


class FrequencyCap:

    def __init__(self, daily_limit=3, hourly_limit=1):
        self.daily_limit = daily_limit
        self.hourly_limit = hourly_limit

        self.daily_counts = defaultdict(int)
        self.hourly_counts = defaultdict(int)

    def reset(self):
        self.daily_counts.clear()
        self.hourly_counts.clear()

    def can_serve(self, campaign_id, user_id, timestamp):

        date = timestamp[:10]
        hour = timestamp[:13]

        daily_key = (campaign_id, user_id, date)
        hourly_key = (campaign_id, user_id, hour)

        if self.daily_counts[daily_key] >= self.daily_limit:
            return False

        if self.hourly_counts[hourly_key] >= self.hourly_limit:
            return False

        return True

    def record_impression(self, campaign_id, user_id, timestamp):

        date = timestamp[:10]
        hour = timestamp[:13]

        daily_key = (campaign_id, user_id, date)
        hourly_key = (campaign_id, user_id, hour)

        self.daily_counts[daily_key] += 1
        self.hourly_counts[hourly_key] += 1

    def get_daily_count(self, campaign_id, user_id, date):

        key = (campaign_id, user_id, date)

        return self.daily_counts[key]

    def get_hourly_count(self, campaign_id, user_id, timestamp):

        key = (campaign_id, user_id, timestamp[:13])

        return self.hourly_counts[key]