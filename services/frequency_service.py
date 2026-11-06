from collections import defaultdict


class FrequencyService:
    """
    Tracks frequency caps per user per campaign in IST per BR-02 and EC-05.
    - Max 3 impressions per user per campaign per calendar day
    - Max 1 impression per user per campaign per clock hour
    """
    def __init__(self):
        self.daily_counts = defaultdict(int)
        self.hourly_counts = defaultdict(int)

    def open_day(self):
        # Open day does not necessarily wipe historical dates, but daily_key includes request_date
        pass

    def get_counts(self, campaign_id, user_id, request_date, request_hour):
        daily_key = (campaign_id, user_id, str(request_date))
        hourly_key = (campaign_id, user_id, str(request_date), int(request_hour))
        return self.daily_counts[daily_key], self.hourly_counts[hourly_key]

    def can_serve(self, campaign, user_id, request_date, request_hour):
        day_cnt, hr_cnt = self.get_counts(campaign.campaign_id, user_id, request_date, request_hour)
        if day_cnt >= campaign.freq_cap_day:
            return False
        if hr_cnt >= campaign.freq_cap_hour:
            return False
        return True

    def record_impression(self, campaign_id, user_id, request_date, request_hour):
        daily_key = (campaign_id, user_id, str(request_date))
        hourly_key = (campaign_id, user_id, str(request_date), int(request_hour))
        self.daily_counts[daily_key] += 1
        self.hourly_counts[hourly_key] += 1
