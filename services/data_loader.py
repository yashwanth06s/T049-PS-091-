import csv
from datetime import date, datetime
from pathlib import Path

from models.advertiser import Advertiser
from models.publisher import Publisher
from models.campaign import Campaign


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_csv(filename):
    with open(DATA_DIR / filename, "r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def load_advertisers():
    advertisers = {}

    for row in load_csv("advertisers.csv"):
        advertiser = Advertiser(
            advertiser_id=row["advertiser_id"],
            name=row["advertiser_name"],
            account_type=row["account_type"],
            wallet_balance=float(row["wallet_balance"]),
            credit_limit=float(row["credit_limit"])
        )
        advertisers[advertiser.advertiser_id] = advertiser

    return advertisers


def load_publishers():
    publishers = {}

    for row in load_csv("publishers.csv"):
        publisher = Publisher(
            publisher_id=row["publisher_id"],
            name=row["publisher_name"],
            floor_price=float(row["floor_cpm"]),
            monthly_billed_amount=float(row["mtd_billed_before"]),
            rollover_payout=float(row["rollover_payout"])
        )
        publishers[publisher.publisher_id] = publisher

    return publishers


def load_campaigns():
    campaigns = {}

    for row in load_csv("campaigns.csv"):
        campaign = Campaign(
            campaign_id=row["campaign_id"],
            advertiser_id=row["advertiser_id"],
            flight_start=date.fromisoformat(row["flight_start"]),
            flight_end=date.fromisoformat(row["flight_end"]),
            daily_budget=float(row["daily_budget"]),
            bid_type=row["bid_type"],
            max_bid=float(row["max_bid"]),
            target_geos=row["target_geos"].split(";"),
            target_devices=row["target_devices"].split(";"),
            target_categories=row["target_categories"].split(";"),
            freq_cap_day=int(row["freq_cap_day"]),
            freq_cap_hour=int(row["freq_cap_hour"])
        )
        campaigns[campaign.campaign_id] = campaign

    return campaigns


def load_traffic_profile():
    return {
        int(row["hour"]): float(row["pct_of_daily_budget"])
        for row in load_csv("traffic_profile.csv")
    }


def load_campaign_history():
    return [
        {
            "campaign_id": row["campaign_id"],
            "date": date.fromisoformat(row["date"]),
            "impressions": int(row["impressions"]),
            "valid_clicks": int(row["valid_clicks"])
        }
        for row in load_csv("campaign_history.csv")
    ]


def load_ad_requests():
    return [
        {
            **row,
            "request_ts": datetime.strptime(
                row["request_ts"], "%Y-%m-%d %H:%M:%S"
            )
        }
        for row in load_csv("ad_requests.csv")
    ]


def load_clicks():
    return [
        {
            **row,
            "click_ts": datetime.strptime(
                row["click_ts"], "%Y-%m-%d %H:%M:%S"
            )
        }
        for row in load_csv("clicks.csv")
    ]