from datetime import date, datetime, timedelta
from decimal import Decimal
from collections import defaultdict
from pathlib import Path

from services.data_loader import (
    load_advertisers,
    load_publishers,
    load_campaigns,
    load_traffic_profile,
    load_campaign_history,
    load_ad_requests,
    load_clicks
)
from services.bidding import calculate_ctr, calculate_ecpm
from services.eligibility import check_eligibility
from services.budget_service import BudgetService
from services.billing_service import BillingService
from services.frequency_service import FrequencyService
from services.click_service import ClickService
from services.auction import run_second_price_auction
from services.report_service import ReportService


class AdEngine:
    def __init__(self, data_dir=None):
        self.advertisers = load_advertisers()
        self.publishers = load_publishers()
        self.campaigns = load_campaigns()
        self.traffic_profile = load_traffic_profile()
        self.campaign_history = load_campaign_history()
        self.ad_requests = load_ad_requests()
        self.clicks = load_clicks()

        self.budget_service = BudgetService(self.traffic_profile)
        self.billing_service = BillingService(self.advertisers, self.publishers)
        self.frequency_service = FrequencyService()
        self.click_service = ClickService()
        self.report_service = ReportService()

        # Cumulative historical records for CTR calculation (campaign_id, date) -> {"impressions": X, "valid_clicks": Y}
        self.history_records = defaultdict(lambda: {"impressions": 0, "valid_clicks": 0})
        for row in self.campaign_history:
            cid = row["campaign_id"]
            d = row["date"]
            self.history_records[(cid, d)]["impressions"] += row["impressions"]
            self.history_records[(cid, d)]["valid_clicks"] += row["valid_clicks"]

        # Trailing CTR cache per campaign for the current open day
        self.current_trailing_ctrs = {}

        # Tracking served requests: request_id -> {"campaign": Campaign, "publisher": Publisher, "clearing_cpm": Decimal}
        self.served_requests = {}

        # Tracking per day stats: (date, campaign_id) -> stats
        self.daily_stats = defaultdict(lambda: {
            "impressions": 0,
            "valid_clicks": 0,
            "invalid_clicks": 0,
            "unfilled_due_to_throttle": 0
        })

        # Global logs
        self.auction_log_rows = []
        self.daily_report_rows = []

        # Chronological event queue
        self._build_event_queue()
        self.event_cursor = 0
        self.current_day = None

    def _build_event_queue(self):
        events = []
        for req in self.ad_requests:
            events.append({
                "type": "REQUEST",
                "ts": req["request_ts"],
                "priority": 1,  # If same second, click processed first (priority 0)
                "data": req
            })
        for clk in self.clicks:
            events.append({
                "type": "CLICK",
                "ts": clk["click_ts"],
                "priority": 0,
                "data": clk
            })
        # Sort by timestamp ascending, then priority
        events.sort(key=lambda e: (e["ts"], e["priority"]))
        self.event_queue = events

    def open_day(self, date_str):
        self.current_day = date.fromisoformat(date_str)
        self.budget_service.open_day()
        self.frequency_service.open_day()

        # BR-03 / EC-03: Recompute trailing 7-day CTR for CPC campaigns
        start_lookback = self.current_day - timedelta(days=7)
        for cid, campaign in self.campaigns.items():
            if campaign.bid_type == "CPC":
                total_imp = 0
                total_clicks = 0
                for day_offset in range(1, 8):
                    past_d = self.current_day - timedelta(days=day_offset)
                    rec = self.history_records.get((cid, past_d), {"impressions": 0, "valid_clicks": 0})
                    total_imp += rec["impressions"]
                    total_clicks += rec["valid_clicks"]

                ctr = calculate_ctr(total_imp, total_clicks)
                self.current_trailing_ctrs[cid] = ctr

    def process_until(self, until_ts_str):
        target_ts = datetime.strptime(until_ts_str, "%Y-%m-%d %H:%M:%S")

        while self.event_cursor < len(self.event_queue):
            event = self.event_queue[self.event_cursor]
            if event["ts"] > target_ts:
                break
            self.event_cursor += 1

            if event["type"] == "REQUEST":
                self._handle_request(event["data"])
            elif event["type"] == "CLICK":
                self._handle_click(event["data"])

    def _handle_request(self, req):
        req_id = req["request_id"]
        # Numeric sequence part
        seq_num = int(req_id.split("-")[1])
        ts = req["request_ts"]
        req_date = ts.date()
        hour = ts.hour
        pub_id = req["publisher_id"]
        user_id = req["user_id"]
        publisher = self.publishers[pub_id]

        eligible_campaigns = []
        throttled_out_campaigns = []

        # Check eligibility
        for cid, campaign in sorted(self.campaigns.items()):
            adv = self.advertisers[campaign.advertiser_id]
            day_imp, hr_imp = self.frequency_service.get_counts(cid, user_id, req_date, hour)
            daily_spend = self.budget_service.get_spend_today(cid)

            is_eligible, reasons = check_eligibility(
                campaign=campaign,
                advertiser=adv,
                request_geo=req["geo"],
                request_device=req["device"],
                request_category=req["category"],
                request_ts=ts,
                daily_spend=daily_spend,
                user_day_impressions=day_imp,
                user_hour_impressions=hr_imp
            )

            if is_eligible:
                # Check pacing & throttle
                can_bid, pacing_status, reason = self.budget_service.can_bid(campaign, hour, seq_num)
                if can_bid:
                    ctr = self.current_trailing_ctrs.get(cid, Decimal("0.005"))
                    ecpm = calculate_ecpm(campaign, ctr)
                    eligible_campaigns.append({
                        "campaign_id": cid,
                        "campaign": campaign,
                        "ecpm": ecpm,
                        "spend_today": daily_spend
                    })
                else:
                    if pacing_status == "OVER_PACE" and seq_num % 2 != 0:
                        throttled_out_campaigns.append(cid)

        # Run Auction
        auction_result = run_second_price_auction(eligible_campaigns, publisher.floor_price)

        # Handle outcome
        if auction_result["outcome"] == "SERVED":
            winner_cmp = auction_result["winner_campaign"]
            winner_cid = auction_result["winner_campaign_id"]
            clearing_cpm = Decimal(auction_result["clearing_cpm"])
            price_per_imp = auction_result["price_per_impression"]

            # Record impression
            self.frequency_service.record_impression(winner_cid, user_id, req_date, hour)
            self.daily_stats[(req_date, winner_cid)]["impressions"] += 1
            self.history_records[(winner_cid, req_date)]["impressions"] += 1

            self.served_requests[req_id] = {
                "campaign": winner_cmp,
                "publisher": publisher,
                "clearing_cpm": clearing_cpm,
                "ts": ts
            }

            # If CPM, bill immediately
            if winner_cmp.bid_type == "CPM":
                self.billing_service.charge_impression(winner_cmp.advertiser_id, pub_id, clearing_cpm)
                self.budget_service.record_spend(winner_cid, hour, price_per_imp)
        else:
            # Unfilled
            if throttled_out_campaigns:
                # EC-04: If unfilled and campaigns were throttled out
                for cid in throttled_out_campaigns:
                    self.daily_stats[(req_date, cid)]["unfilled_due_to_throttle"] += 1

        self.auction_log_rows.append({
            "request_id": req_id,
            "outcome": auction_result["outcome"],
            "winner_campaign_id": auction_result["winner_campaign_id"],
            "winner_ecpm": auction_result["winner_ecpm"],
            "second_ecpm": auction_result["second_ecpm"],
            "clearing_cpm": auction_result["clearing_cpm"],
            "bidders": auction_result["bidders"],
            "reason": auction_result["reason"]
        })

    def _handle_click(self, clk):
        req_id = clk["request_id"]
        if req_id not in self.served_requests:
            return

        served = self.served_requests[req_id]
        campaign = served["campaign"]
        publisher = served["publisher"]
        cid = campaign.campaign_id
        click_date = clk["click_ts"].date()

        record = self.click_service.process_click(
            click=clk,
            campaign=campaign,
            publisher=publisher,
            budget_service=self.budget_service,
            billing_service=self.billing_service
        )

        if record["status"] == "VALID":
            self.daily_stats[(click_date, cid)]["valid_clicks"] += 1
            self.history_records[(cid, click_date)]["valid_clicks"] += 1
        else:
            self.daily_stats[(click_date, cid)]["invalid_clicks"] += 1

    def close_day(self, date_str):
        d = date.fromisoformat(date_str)
        # Generate daily report row for every campaign
        for cid in sorted(self.campaigns.keys()):
            campaign = self.campaigns[cid]
            stats = self.daily_stats[(d, cid)]
            spend = self.budget_service.get_spend_today(cid)
            budget = Decimal(str(campaign.daily_budget))
            pacing_status = self.budget_service.get_pacing_status(campaign, 23)

            # Recompute valid vs invalid clicks directly from click_service
            # in case clicks were retroactively invalidated by IVT
            c_clicks = [c for c in self.click_service.clicks if c["campaign_id"] == cid and c["click_ts"].date() == d]
            valid_c = sum(1 for c in c_clicks if c["status"] == "VALID")
            invalid_c = sum(1 for c in c_clicks if c["status"] == "INVALID")

            row = {
                "date": date_str,
                "campaign_id": cid,
                "impressions": stats["impressions"],
                "valid_clicks": valid_c,
                "invalid_clicks": invalid_c,
                "spend": f"{spend:.2f}",
                "budget": f"{budget:.2f}",
                "pacing_status_end": pacing_status,
                "unfilled_due_to_throttle": stats["unfilled_due_to_throttle"]
            }
            self.daily_report_rows.append(row)

    def print_daily_report(self, date_str):
        day_rows = [r for r in self.daily_report_rows if r["date"] == date_str]
        print(f"\n--- DAILY CAMPAIGN REPORT for {date_str} ---")
        for r in day_rows:
            print(f"{r['campaign_id']}: Imp={r['impressions']} Clicks={r['valid_clicks']} Invalid={r['invalid_clicks']} Spend=Rs.{r['spend']} Budget=Rs.{r['budget']} Status={r['pacing_status_end']} ThrottledUnfilled={r['unfilled_due_to_throttle']}")

    def print_publisher_payout(self, month_str):
        payouts = self.billing_service.generate_all_publisher_payouts()
        print(f"\n--- PUBLISHER PAYOUT for {month_str} ---")
        for p in payouts:
            print(f"{p['publisher_id']}: MTD Billed=Rs.{p['mtd_billed']} Share%={p['share_pct']} Share=Rs.{p['share_amount']} Clawback=Rs.{p['clawback']} RolloverIn=Rs.{p['rollover_in']} Due=Rs.{p['payout_due']} RolledNext=Rs.{p['rolled_to_next']}")

    def print_auction_log(self, from_date_str, to_date_str):
        print(f"\n--- AUCTION LOG ({from_date_str} to {to_date_str}) ---")
        print(f"Total Requests Processed: {len(self.auction_log_rows)}")

    def export_all_reports(self, output_dir="output"):
        self.report_service.output_dir = Path(output_dir)
        self.report_service.output_dir.mkdir(parents=True, exist_ok=True)

        self.report_service.write_auction_log(self.auction_log_rows)
        self.report_service.write_click_log(self.click_service.get_clicks_for_report())
        self.report_service.write_daily_campaign_report(self.daily_report_rows)
        self.report_service.write_publisher_payout(self.billing_service.generate_all_publisher_payouts())
