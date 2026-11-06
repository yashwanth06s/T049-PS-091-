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


# --- BR-01: Eligibility & Targeting ---

def test_br01_targeting_match():
    camp = Campaign(
        campaign_id="CMP-101", advertiser_id="ADV-01",
        flight_start=date(2026, 10, 1), flight_end=date(2026, 10, 31),
        daily_budget=1000.0, bid_type="CPM", max_bid=50.0,
        target_geos=["KA", "MH"], target_devices=["MOBILE"], target_categories=["TECH"],
        freq_cap_day=3, freq_cap_hour=1
    )
    adv = Advertiser("ADV-01", "TechAdv", "PREPAID", 1000.0, 0.0)

    # All match
    ok, _ = check_eligibility(camp, adv, "KA", "MOBILE", "TECH", datetime(2026, 10, 5, 12, 0), 0)
    assert ok

    # Geo mismatch
    ok, reasons = check_eligibility(camp, adv, "DL", "MOBILE", "TECH", datetime(2026, 10, 5, 12, 0), 0)
    assert not ok
    assert "Geographical targeting mismatch" in reasons


def test_br01_flight_dates():
    camp = Campaign(
        campaign_id="CMP-102", advertiser_id="ADV-01",
        flight_start=date(2026, 10, 5), flight_end=date(2026, 10, 10),
        daily_budget=1000.0, bid_type="CPM", max_bid=50.0,
        target_geos=["ALL"], target_devices=["ALL"], target_categories=["ALL"],
        freq_cap_day=3, freq_cap_hour=1
    )
    adv = Advertiser("ADV-01", "TechAdv", "PREPAID", 1000.0, 0.0)

    # Before start
    ok, reasons = check_eligibility(camp, adv, "KA", "MOBILE", "TECH", datetime(2026, 10, 4, 23, 59), 0)
    assert not ok
    assert "Campaign flight has not started" in reasons

    # After end
    ok, reasons = check_eligibility(camp, adv, "KA", "MOBILE", "TECH", datetime(2026, 10, 11, 0, 0), 0)
    assert not ok
    assert "Campaign flight has ended" in reasons


def test_br01_budget_and_wallet_limits():
    camp = Campaign(
        campaign_id="CMP-103", advertiser_id="ADV-01",
        flight_start=date(2026, 10, 1), flight_end=date(2026, 10, 31),
        daily_budget=500.0, bid_type="CPM", max_bid=100.0,
        target_geos=["ALL"], target_devices=["ALL"], target_categories=["ALL"],
        freq_cap_day=3, freq_cap_hour=1
    )
    adv = Advertiser("ADV-01", "TechAdv", "PREPAID", 0.05, 0.0)  # less than 100/1000 = 0.10

    # Insufficient wallet
    ok, reasons = check_eligibility(camp, adv, "KA", "MOBILE", "TECH", datetime(2026, 10, 5, 12, 0), 0)
    assert not ok
    assert any("Insufficient prepaid wallet" in r for r in reasons)

    # Budget exhausted
    adv.wallet_balance = 500.0
    ok, reasons = check_eligibility(camp, adv, "KA", "MOBILE", "TECH", datetime(2026, 10, 5, 12, 0), 500.0)
    assert not ok
    assert "Daily budget exhausted" in reasons


# --- BR-02: Frequency Capping ---

def test_br02_frequency_limits():
    fs = FrequencyService()
    camp = Campaign(
        campaign_id="CMP-104", advertiser_id="ADV-01",
        flight_start=date(2026, 10, 1), flight_end=date(2026, 10, 31),
        daily_budget=1000.0, bid_type="CPM", max_bid=50.0,
        target_geos=["ALL"], target_devices=["ALL"], target_categories=["ALL"],
        freq_cap_day=3, freq_cap_hour=1
    )
    u = "U1001"
    d = date(2026, 10, 12)

    # 1st impression in hour 10
    assert fs.can_serve(camp, u, d, 10)
    fs.record_impression("CMP-104", u, d, 10)

    # 2nd in same hour blocked
    assert not fs.can_serve(camp, u, d, 10)

    # 2nd in hour 11 allowed
    assert fs.can_serve(camp, u, d, 11)
    fs.record_impression("CMP-104", u, d, 11)

    # 3rd in hour 12 allowed
    assert fs.can_serve(camp, u, d, 12)
    fs.record_impression("CMP-104", u, d, 12)

    # 4th in hour 13 blocked (daily cap 3 reached)
    assert not fs.can_serve(camp, u, d, 13)


# --- BR-03: Bid Normalisation ---

def test_br03_ecpm_conversions():
    cpm_camp = Campaign(
        campaign_id="CMP-105", advertiser_id="ADV-01",
        flight_start=date(2026, 10, 1), flight_end=date(2026, 10, 31),
        daily_budget=1000.0, bid_type="CPM", max_bid=75.0,
        target_geos=["ALL"], target_devices=["ALL"], target_categories=["ALL"],
        freq_cap_day=3, freq_cap_hour=1
    )
    cpc_camp = Campaign(
        campaign_id="CMP-106", advertiser_id="ADV-01",
        flight_start=date(2026, 10, 1), flight_end=date(2026, 10, 31),
        daily_budget=1000.0, bid_type="CPC", max_bid=10.0,
        target_geos=["ALL"], target_devices=["ALL"], target_categories=["ALL"],
        freq_cap_day=3, freq_cap_hour=1
    )
    # CPM returns max_bid
    assert calculate_ecpm(cpm_camp) == Decimal("75.0")

    # CPC with default 0.5% CTR: 10 * 0.005 * 1000 = 50.0
    assert calculate_ecpm(cpc_camp, Decimal("0.005")) == Decimal("50.000")

    # CPC with 1.2% CTR: 10 * 0.012 * 1000 = 120.0
    assert calculate_ecpm(cpc_camp, Decimal("0.012")) == Decimal("120.000")


# --- BR-04 & BR-05: Second-Price Auction & Ties ---

def test_br04_auction_clearing_and_ties():
    c1 = Campaign(
        campaign_id="CMP-A", advertiser_id="ADV-01",
        flight_start=date(2026, 10, 1), flight_end=date(2026, 10, 31),
        daily_budget=1000.0, bid_type="CPM", max_bid=100.0,
        target_geos=["ALL"], target_devices=["ALL"], target_categories=["ALL"],
        freq_cap_day=3, freq_cap_hour=1
    )
    c2 = Campaign(
        campaign_id="CMP-B", advertiser_id="ADV-01",
        flight_start=date(2026, 10, 1), flight_end=date(2026, 10, 31),
        daily_budget=1000.0, bid_type="CPM", max_bid=100.0,
        target_geos=["ALL"], target_devices=["ALL"], target_categories=["ALL"],
        freq_cap_day=3, freq_cap_hour=1
    )
    candidates = [
        {"campaign_id": "CMP-A", "campaign": c1, "ecpm": Decimal("100.00"), "spend_today": Decimal("50.00")},
        {"campaign_id": "CMP-B", "campaign": c2, "ecpm": Decimal("100.00"), "spend_today": Decimal("20.00")},
    ]
    # Tie-break: CMP-B has lower cumulative spend today (20.00 < 50.00)
    res = run_second_price_auction(candidates, floor_price=50.00)
    assert res["winner_campaign_id"] == "CMP-B"
    # Second highest is 100.00 -> clearing = 100.01
    assert res["clearing_cpm"] == "100.01"


# --- BR-06 & BR-07: Pacing & Throttling ---

def test_br06_br07_pacing_and_throttling():
    profile = {h: 4.166 for h in range(24)}  # flat profile
    bs = BudgetService(profile)
    c = Campaign(
        campaign_id="CMP-201", advertiser_id="ADV-01",
        flight_start=date(2026, 10, 1), flight_end=date(2026, 10, 31),
        daily_budget=2400.0, bid_type="CPM", max_bid=100.0,
        target_geos=["ALL"], target_devices=["ALL"], target_categories=["ALL"],
        freq_cap_day=3, freq_cap_hour=1
    )
    # Hour 0 scheduled = 100.00. Spend = 50.00 -> UNDER_PACE
    bs.record_spend("CMP-201", 0, Decimal("50.00"))
    assert bs.get_pacing_status(c, 0) == "UNDER_PACE"

    # Catch-up allows up to 150% of hour bucket (150.00)
    can_bid, _, _ = bs.can_bid(c, 0, 1)
    assert can_bid

    # Spend reaches 130.00 at hour 0 (cumulative scheduled 100.00) -> > 120% -> OVER_PACE
    bs.record_spend("CMP-201", 0, Decimal("80.00"))  # total 130.00
    assert bs.get_pacing_status(c, 0) == "OVER_PACE"

    # Odd request sequence throttled
    can_bid, status, _ = bs.can_bid(c, 0, 101)
    assert not can_bid
    assert status == "OVER_PACE"

    # Even request sequence allowed
    can_bid, status, _ = bs.can_bid(c, 0, 102)
    assert can_bid


# --- BR-08 & BR-09: Billing & Credit Accounts ---

def test_br08_br09_billing_and_credit():
    adv_pre = Advertiser("ADV-PRE", "Pre", "PREPAID", 10.0, 0.0)
    adv_crd = Advertiser("ADV-CRD", "Crd", "CREDIT", 0.0, 100.0)
    pub = Publisher("PUB-1", "News", 50.0, 0.0, 0.0)
    billing = BillingService({"ADV-PRE": adv_pre, "ADV-CRD": adv_crd}, {"PUB-1": pub})

    # Prepaid charge
    billing.charge_impression("ADV-PRE", "PUB-1", 5000.0)  # 5.00
    assert adv_pre.wallet_balance == pytest.approx(5.0)

    # Credit charge down past limit
    billing.charge_impression("ADV-CRD", "PUB-1", 100010.0)  # 100.01
    assert adv_crd.wallet_balance == pytest.approx(-100.01)
    assert adv_crd.suspended is True


# --- BR-10: IVT Detection & Reversal ---

def test_br10_ivt_detection():
    cs = ClickService()
    profile = {0: 100.0}
    bs = BudgetService(profile)
    adv = Advertiser("ADV-10", "Adv", "PREPAID", 1000.0, 0.0)
    pub = Publisher("PUB-1", "Pub", 50.0, 10000.0, 0.0)
    billing = BillingService({"ADV-10": adv}, {"PUB-1": pub})
    camp = Campaign(
        campaign_id="CMP-301", advertiser_id="ADV-10",
        flight_start=date(2026, 10, 1), flight_end=date(2026, 10, 31),
        daily_budget=1000.0, bid_type="CPC", max_bid=10.0,
        target_geos=["ALL"], target_devices=["ALL"], target_categories=["ALL"],
        freq_cap_day=3, freq_cap_hour=1
    )
    t0 = datetime(2026, 10, 12, 10, 0, 0)
    # 5 clicks within 5 minutes -> still VALID
    for i in range(5):
        cs.process_click({
            "click_id": f"CLK-{i}", "request_id": f"REQ-{i}", "user_id": "U1",
            "click_ts": t0 + timedelta(minutes=i)
        }, camp, pub, bs, billing)
    assert all(c["status"] == "VALID" for c in cs.clicks)

    # 6th click within 10 min window -> all become INVALID
    cs.process_click({
        "click_id": "CLK-5", "request_id": "REQ-5", "user_id": "U1",
        "click_ts": t0 + timedelta(minutes=8)
    }, camp, pub, bs, billing)
    assert all(c["status"] == "INVALID" for c in cs.clicks)
    assert all(c["reversed"] is True for c in cs.clicks)


# --- BR-11: Publisher Payout & Tiers ---

def test_br11_publisher_tiers_and_rollover():
    # Below 100k -> 60%
    p1 = Publisher("PUB-A", "SmallPub", 50.0, 50000.0, 0.0)
    # Above 100k -> 70%
    p2 = Publisher("PUB-B", "BigPub", 50.0, 150000.0, 0.0)
    billing = BillingService({}, {"PUB-A": p1, "PUB-B": p2})

    payout_a = billing.get_publisher_payout("PUB-A")
    assert payout_a["share_pct"] == 60

    payout_b = billing.get_publisher_payout("PUB-B")
    assert payout_b["share_pct"] == 70

    # Rollover under 5,000
    p3 = Publisher("PUB-C", "TinyPub", 50.0, 1000.0, 0.0)
    billing_small = BillingService({}, {"PUB-C": p3})
    payout_c = billing_small.get_publisher_payout("PUB-C")
    assert payout_c["payout_due"] == "0.00"
    assert Decimal(payout_c["rolled_to_next"]) > 0
