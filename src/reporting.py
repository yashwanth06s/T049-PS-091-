import csv
import os


class ReportGenerator:

    def __init__(self, output_folder="output"):
        self.output_folder = output_folder
        os.makedirs(self.output_folder, exist_ok=True)

    def write_csv(self, filename, headers, rows):

        filepath = os.path.join(
            self.output_folder, filename
        )

        with open(
            filepath, "w", newline="", encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=headers
            )

            writer.writeheader()
            writer.writerows(rows)

        return filepath

    def generate_daily_report(self, rows):

        headers = [
            "date",
            "campaign_id",
            "impressions",
            "valid_clicks",
            "invalid_clicks",
            "spend",
            "budget",
            "pacing_status_end",
            "unfilled_due_to_throttle"
        ]

        return self.write_csv(
            "daily_campaign_report.csv",
            headers,
            rows
        )

    def generate_auction_log(self, rows):

        headers = [
            "request_id",
            "outcome",
            "winner_campaign_id",
            "winner_ecpm",
            "second_ecpm",
            "clearing_cpm",
            "bidders",
            "reason"
        ]

        return self.write_csv(
            "auction_log.csv",
            headers,
            rows
        )

    def generate_click_log(self, rows):

        headers = [
            "click_id",
            "request_id",
            "campaign_id",
            "status",
            "billed_amount",
            "reversed"
        ]

        return self.write_csv(
            "click_log.csv",
            headers,
            rows
        )

    def generate_publisher_payout(self, rows):

        headers = [
            "publisher_id",
            "mtd_billed",
            "share_pct",
            "share_amount",
            "clawback",
            "rollover_in",
            "payout_due",
            "rolled_to_next"
        ]

        return self.write_csv(
            "publisher_payout.csv",
            headers,
            rows
        )