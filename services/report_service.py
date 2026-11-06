import csv
from pathlib import Path


class ReportService:
    def __init__(self, output_dir="output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_csv(self, filename, headers, rows):
        path = self.output_dir / filename
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def write_auction_log(self, rows, filename="auction_log.csv"):
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
        return self.write_csv(filename, headers, rows)

    def write_click_log(self, rows, filename="click_log.csv"):
        headers = [
            "click_id",
            "request_id",
            "campaign_id",
            "status",
            "billed_amount",
            "reversed"
        ]
        return self.write_csv(filename, headers, rows)

    def write_daily_campaign_report(self, rows, filename="daily_campaign_report.csv"):
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
        return self.write_csv(filename, headers, rows)

    def write_publisher_payout(self, rows, filename="publisher_payout.csv"):
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
        return self.write_csv(filename, headers, rows)
