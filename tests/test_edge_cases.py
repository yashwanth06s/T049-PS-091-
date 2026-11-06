from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest

from models.campaign import Campaign
from models.publisher import Publisher
from models.advertiser import Advertiser
from services.auction import run_second_price_auction
from services.bidding import calculate_ctr, calculate_ecpm
from services.budget_service import BudgetService
from services.billing_service import BillingService
from services.frequency_service import FrequencyService
from services.click_service import ClickService
from services.eligibility import check_eligibility


def test_ec01_single_bidder_pays_floor_exactly():
    """
    EC-01: Single bidder whose bid equals the floor pays the floor exactly without increment.
    """
    camp = Campaign(
        campaign_id="CMP-001",
        advertiser_id="ADV-05",
        flight_start=date(2026, 10, 12),
        flight_end=date(2026, 10, 14),
        daily_budget=400.0,
        bid_type="CPM",
        max_bid=150.0,
        target_geos=["KA"],
        target_devices=["MOBILE"],
        target_categories=["AGRITECH"],
        freq_cap_day=3,
        freq_cap_hour=1
    )
    candidates = [{
        "campaign_id": "CMP-001",
        "campaign": camp,
        "ecpm": Decimal("150.00"),
        "spend_today": Decimal("0.00")
    }]
    res = run_second_price_auction(candidates, floor_price=150.00)
    assert res["outcome"] == "SERVED"
    assert res["winner_campaign_id"] == "CMP-001"
    assert res["clearing_cpm"] == "150.00"
    assert res["price_per_impression"] == Decimal("0.15")


def test_ec02_second_highest_bid_below_floor():
    """
    EC-02: Second-highest bid below floor -> winner pays floor plus Rs 0.01 increment.
    """
    c4 = Campaign(
        campaign_id="CMP-004", advertiser_id="ADV-01",
        flight_start=date(2026, 10, 12), flight_end=date(2026, 10, 14),
        daily_budget=4000.0, bid_type="CPM", max_bid=180.0,
        target_geos=["KA"], target_devices=["DESKTOP"], target_categories=["REAL_ESTATE"],
        freq_cap_day=3, freq_cap_hour=1
    )
    c5 = Campaign(
        campaign_id="CMP-005", advertiser_id="ADV-03",
        flight_start=date(2026, 10, 12), flight_end=date(2026, 10, 14),
        daily_budget=4000.0, bid_type="CPM", max_bid=90.0,
        target_geos=["KA"], target_devices=["DESKTOP"], target_categories=["REAL_ESTATE"],
        freq_cap_day=3, freq_cap_hour=1
    )
    candidates = [
        {"campaign_id": "CMP-004", "campaign": c4, "ecpm": Decimal("180.00"), "spend_today": Decimal("0.00")},
        {"campaign_id": "CMP-005", "campaign": c5, "ecpm": Decimal("90.00"), "spend_today": Decimal("0.00")},
    ]
    res = run_second_price_auction(candidates, floor_price=120.00)
    assert res["outcome"] == "SERVED"
    assert res["winner_campaign_id"] == "CMP-004"
    assert res["second_ecpm"] == "90.00"
    assert res["clearing_cpm"] == "120.01"


def test_ec03_cpc_exactly_1000_impressions():
    """
    EC-03: Exactly 1,000 trailing impressions switches from 0.5% default CTR to actual CTR.
    """
    assert calculate_ctr(999, 7) == Decimal("0.005")
    assert calculate_ctr(1000, 7) == Decimal("0.007")
    camp = Campaign(
        campaign_id="CMP-006", advertiser_id="ADV-08",
        flight_start=date(2026, 10, 12), flight_end=date(2026, 10, 14),
        daily_budget=2500.0, bid_type="CPC", max_bid=25.0,
        target_geos=["KA"], target_devices=["MOBILE"], target_categories=["EDUCATION"],
        freq_cap_day=3, freq_cap_hour=1
    )
    ecpm = calculate_ecpm(camp, calculate_ctr(1000, 7))
    assert ecpm == Decimal("175.000")


def test_ec04_pacing_at_120_percent():
    """
    EC-04: Campaign at 120.0% of scheduled budget is OVER_PACE and throttled on odd sequence.
    """
    traffic_profile = {0: 1.5, 1: 1.0}
    bs = BudgetService(traffic_profile)
    c1 = Campaign(
        campaign_id="CMP-001", advertiser_id="ADV-05",
        flight_start=date(2026, 10, 12), flight_end=date(2026, 10, 14),
        daily_budget=400.0, bid_type="CPM", max_bid=150.0,
        target_geos=["KA"], target_devices=["MOBILE"], target_categories=["AGRITECH"],
        freq_cap_day=3, freq_cap_hour=1
    )
    # Hour 0 scheduled budget: 400 * 1.5% = 6.00. 120% = 7.20.
    bs.record_spend("CMP-001", 0, Decimal("7.20"))
    assert bs.get_pacing_status(c1, 0) == "OVER_PACE"
    # Odd sequence number (519) sits out
    can_bid, status, reason = bs.can_bid(c1, 0, 519)
    assert not can_bid
    # Even sequence number (520) allowed
    can_bid, status, reason = bs.can_bid(c1, 0, 520)
    assert can_bid


def test_ec05_frequency_cap_day_hour_boundary():
    """
    EC-05: 3rd impression of day served, next in same day capped, but 00:00 next day served.
    """
    fs = FrequencyService()
    c2 = Campaign(
        campaign_id="CMP-002", advertiser_id="ADV-06",
        flight_start=date(2026, 10, 12), flight_end=date(2026, 10, 14),
        daily_budget=3000.0, bid_type="CPM", max_bid=170.0,
        target_geos=["KA"], target_devices=["MOBILE"], target_categories=["LEGAL"],
        freq_cap_day=3, freq_cap_hour=1
    )
    user = "U77770001"
    # 2 prior impressions
    fs.record_impression("CMP-002", user, date(2026, 10, 12), 10)
    fs.record_impression("CMP-002", user, date(2026, 10, 12), 14)

    # 3rd impression at 23:59:00
    assert fs.can_serve(c2, user, date(2026, 10, 12), 23)
    fs.record_impression("CMP-002", user, date(2026, 10, 12), 23)

    # Request at 23:59:30 should be capped
    assert not fs.can_serve(c2, user, date(2026, 10, 12), 23)

    # Request at 00:00:00 next day should be eligible
    assert fs.can_serve(c2, user, date(2026, 10, 13), 0)


def test_ec06_ivt_sliding_window():
    """
    EC-06: 6 clicks from same user on same campaign within 10 minutes marks all 6 INVALID.
    """
    cs = ClickService()
    profile = {0: 100.0}
    bs = BudgetService(profile)
    advs = {"ADV-08": Advertiser("ADV-08", "SkillUp", "PREPAID", 50000.0, 0.0)}
    pubs = {"PUB-4": Publisher("PUB-4", "Mint Street", 120.0, 30000.0, 0.0)}
    billing = BillingService(advs, pubs)

    c6 = Campaign(
        campaign_id="CMP-006", advertiser_id="ADV-08",
        flight_start=date(2026, 10, 12), flight_end=date(2026, 10, 14),
        daily_budget=2500.0, bid_type="CPC", max_bid=25.0,
        target_geos=["KA"], target_devices=["MOBILE"], target_categories=["EDUCATION"],
        freq_cap_day=3, freq_cap_hour=1
    )
    pub = pubs["PUB-4"]

    base_time = datetime(2026, 10, 13, 10, 0, 0)
    clicks = []
    for i in range(6):
        click_data = {
            "click_id": f"CLK-{i+1:05d}",
            "request_id": "REQ-000740",
            "user_id": "U66660042",
            "click_ts": base_time + timedelta(minutes=2 * i)
        }
        res = cs.process_click(click_data, c6, pub, bs, billing)
        clicks.append(res)

    # All 6 must now be INVALID
    assert all(c["status"] == "INVALID" for c in clicks)
    assert all(c["reversed"] is True for c in clicks)
    # Publisher clawback: 6 * 25 = 150 * 60% = 90.00
    assert billing.publisher_clawbacks["PUB-4"] == Decimal("90.00")


def test_ec07_publisher_at_exactly_100k():
    """
    EC-07: Publisher at exactly Rs 1,00,000 gets 60% revenue share (not above 100k).
    """
    advs = {"ADV-05": Advertiser("ADV-05", "Agro", "PREPAID", 50000.0, 0.0)}
    pubs = {"PUB-5": Publisher("PUB-5", "Gaon", 150.0, 99982.60, 0.0)}
    billing = BillingService(advs, pubs)
    billing.charge_impression("ADV-05", "PUB-5", 17400.0)  # 17400 / 1000 = 17.40
    payout = billing.get_publisher_payout("PUB-5")
    assert payout["mtd_billed"] == "100000.00"
    assert payout["share_pct"] == 60
    assert payout["share_amount"] == "60000.00"


def test_ec08_credit_advertiser_suspended():
    """
    EC-08: Charge taking credit advertiser balance below -credit_limit stands and suspends advertiser.
    """
    adv = Advertiser("ADV-07", "Pilgrimage", "CREDIT", -49995.51, 50000.0)
    pubs = {"PUB-5": Publisher("PUB-5", "Gaon", 150.0, 99982.60, 0.0)}
    billing = BillingService({"ADV-07": adv}, pubs)

    # 30 wins of 0.15 takes balance to -50000.01 (0.01 beyond limit)
    for _ in range(30):
        billing.charge_impression("ADV-07", "PUB-5", 150.0)

    assert adv.wallet_balance == pytest.approx(-50000.01, 0.001)
    assert adv.suspended is True
