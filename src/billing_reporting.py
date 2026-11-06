import csv
from pathlib import Path

from impression_tracking import ImpressionTracker


class BillingReporting:

    def __init__(self):
        self.tracker = ImpressionTracker()

    # ---------- Impression Tracking ----------

    def record_impression(self, campaign_id, date):
        self.tracker.record_impression(campaign_id, date)

    # ---------- Click Tracking ----------

    def record_valid_click(self, campaign_id, date):
        self.tracker.record_valid_click(campaign_id, date)

    def record_invalid_click(self, campaign_id, date):
        self.tracker.record_invalid_click(campaign_id, date)

    # ---------- Campaign Statistics ----------

    def get_campaign_summary(self, campaign_id, date):

        impressions = self.tracker.get_impressions(
            campaign_id, date
        )

        valid_clicks = self.tracker.get_valid_clicks(
            campaign_id, date
        )

        invalid_clicks = self.tracker.get_invalid_clicks(
            campaign_id, date
        )

        total_clicks = valid_clicks + invalid_clicks

        ctr = (
            (valid_clicks / impressions) * 100
            if impressions > 0 else 0
        )

        return {
            "campaign_id": campaign_id,
            "date": date,
            "impressions": impressions,
            "valid_clicks": valid_clicks,
            "invalid_clicks": invalid_clicks,
            "total_clicks": total_clicks,
            "ctr": round(ctr, 2)
        }

    # ---------- Daily Reporting ----------

    def generate_daily_report(
        self,
        campaign_ids,
        date,
        filename="daily_campaign_report.csv"
    ):

        report_data = []

        for campaign_id in campaign_ids:
            summary = self.get_campaign_summary(
                campaign_id, date
            )

            report_data.append(summary)

        if not report_data:
            return report_data

        with open(
            filename,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=report_data[0].keys()
            )

            writer.writeheader()
            writer.writerows(report_data)

        return report_data