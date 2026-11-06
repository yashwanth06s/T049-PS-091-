from collections import defaultdict
from datetime import datetime, timedelta


class InvalidTrafficDetector:

    def __init__(self):
        self.clicks = defaultdict(list)
        self.invalid_click_ids = set()

    def add_click(self, click_id, campaign_id, user_id, click_ts):

        timestamp = datetime.strptime(
            click_ts, "%Y-%m-%d %H:%M:%S"
        )

        key = (campaign_id, user_id)

        self.clicks[key].append({
            "click_id": click_id,
            "timestamp": timestamp
        })

    def detect_invalid_clicks(self):

        self.invalid_click_ids.clear()

        for key, click_list in self.clicks.items():

            sorted_clicks = sorted(
                click_list,
                key=lambda click: click["timestamp"]
            )

            left = 0

            for right in range(len(sorted_clicks)):

                while (
                    sorted_clicks[right]["timestamp"]
                    - sorted_clicks[left]["timestamp"]
                    > timedelta(minutes=10)
                ):
                    left += 1

                if right - left + 1 >= 6:

                    for index in range(left, right + 1):
                        self.invalid_click_ids.add(
                            sorted_clicks[index]["click_id"]
                        )

        return self.invalid_click_ids

    def is_invalid(self, click_id):
        return click_id in self.invalid_click_ids

    def get_invalid_clicks(self):
        return self.invalid_click_ids.copy()