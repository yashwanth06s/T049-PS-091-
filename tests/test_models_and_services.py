from datetime import date, datetime
from decimal import Decimal
import pytest

from models.campaign import Campaign
from models.publisher import Publisher
from models.advertiser import Advertiser
from services.bidding import calculate_ctr, calculate_ecpm, validate_bid
from services.budget_service import BudgetService
from services.billing_service import BillingService
from services.frequency_service import FrequencyService
from services.data_loader import (
    load_advertisers,
    load_publishers,
    load_campaigns,
    load_traffic_profile
)


# --- Model Validations ---

def test_advertiser_empty_id_raises():
    with pytest.raises(ValueError, match="Advertiser ID cannot be empty"):
        Advertiser("", "Name", "PREPAID", 100.0, 0.0)


def test_advertiser_empty_name_raises():
    with pytest.raises(ValueError, match="Advertiser name cannot be empty"):
        Advertiser("ADV-1", "", "PREPAID", 100.0, 0.0)


def test_advertiser_invalid_account_type_raises():
    with pytest.raises(ValueError, match="Account type must be PREPAID or CREDIT"):
        Advertiser("ADV-1", "Name", "POSTPAID", 100.0, 0.0)


def test_advertiser_negative_credit_limit_raises():
    with pytest.raises(ValueError, match="Credit limit cannot be negative"):
        Advertiser("ADV-1", "Name", "CREDIT", 0.0, -100.0)


def test_advertiser_prepaid_negative_balance_raises():
    with pytest.raises(ValueError, match="Prepaid wallet cannot be negative"):
        Advertiser("ADV-1", "Name", "PREPAID", -50.0, 0.0)


def test_advertiser_credit_exceeds_limit_at_init_raises():
    with pytest.raises(ValueError, match="Balance exceeds credit limit"):
        Advertiser("ADV-1", "Name", "CREDIT", -150.0, 100.0)


def test_campaign_invalid_flight_dates_raises():
    with pytest.raises(ValueError, match="Invalid campaign flight dates"):
        Campaign(
            "CMP-1", "ADV-1", date(2026, 10, 15), date(2026, 10, 10),
            1000.0, "CPM", 50.0, ["ALL"], ["ALL"], ["ALL"], 3, 1
        )


def test_campaign_non_positive_budget_raises():
    with pytest.raises(ValueError, match="Budget and bid must be positive"):
        Campaign(
            "CMP-1", "ADV-1", date(2026, 10, 1), date(2026, 10, 10),
            0.0, "CPM", 50.0, ["ALL"], ["ALL"], ["ALL"], 3, 1
        )


def test_campaign_non_positive_bid_raises():
    with pytest.raises(ValueError, match="Budget and bid must be positive"):
        Campaign(
            "CMP-1", "ADV-1", date(2026, 10, 1), date(2026, 10, 10),
            1000.0, "CPM", 0.0, ["ALL"], ["ALL"], ["ALL"], 3, 1
        )


def test_campaign_invalid_bid_type_raises():
    with pytest.raises(ValueError, match="Bid type must be CPM or CPC"):
        Campaign(
            "CMP-1", "ADV-1", date(2026, 10, 1), date(2026, 10, 10),
            1000.0, "CPA", 50.0, ["ALL"], ["ALL"], ["ALL"], 3, 1
        )


def test_campaign_non_positive_freq_cap_raises():
    with pytest.raises(ValueError, match="Frequency caps must be positive"):
        Campaign(
            "CMP-1", "ADV-1", date(2026, 10, 1), date(2026, 10, 10),
            1000.0, "CPM", 50.0, ["ALL"], ["ALL"], ["ALL"], 0, 1
        )


def test_publisher_empty_id_raises():
    with pytest.raises(ValueError, match="Publisher ID cannot be empty"):
        Publisher("", "Pub", 50.0, 0.0, 0.0)


def test_publisher_empty_name_raises():
    with pytest.raises(ValueError, match="Publisher name cannot be empty"):
        Publisher("PUB-1", "", 50.0, 0.0, 0.0)


def test_publisher_negative_floor_raises():
    with pytest.raises(ValueError, match="Floor price cannot be negative"):
        Publisher("PUB-1", "Pub", -10.0, 0.0, 0.0)


def test_publisher_negative_monthly_billed_raises():
    with pytest.raises(ValueError, match="Monthly billed amount cannot be negative"):
        Publisher("PUB-1", "Pub", 50.0, -100.0, 0.0)


def test_publisher_negative_rollover_raises():
    with pytest.raises(ValueError, match="Rollover payout cannot be negative"):
        Publisher("PUB-1", "Pub", 50.0, 0.0, -50.0)


# --- Service Edge Calculations ---

def test_bidding_validate_bid():
    camp = Campaign("C", "A", date(2026, 10, 1), date(2026, 10, 10), 100.0, "CPM", 10.0, ["ALL"], ["ALL"], ["ALL"], 3, 1)
    assert validate_bid(camp) is True


def test_budget_service_open_day_resets_spend():
    profile = {0: 100.0}
    bs = BudgetService(profile)
    bs.record_spend("CMP-1", 0, Decimal("50.00"))
    assert bs.get_spend_today("CMP-1") == Decimal("50.00")
    bs.open_day()
    assert bs.get_spend_today("CMP-1") == Decimal("0.00")


def test_frequency_service_get_counts():
    fs = FrequencyService()
    fs.record_impression("CMP-1", "U1", date(2026, 10, 12), 5)
    day_cnt, hr_cnt = fs.get_counts("CMP-1", "U1", date(2026, 10, 12), 5)
    assert day_cnt == 1
    assert hr_cnt == 1


def test_billing_can_afford_prepaid():
    adv = Advertiser("ADV-1", "Adv", "PREPAID", 10.0, 0.0)
    billing = BillingService({"ADV-1": adv}, {})
    assert billing.can_afford("ADV-1", Decimal("10.00")) is True
    assert billing.can_afford("ADV-1", Decimal("10.01")) is False


def test_data_loader_counts():
    advs = load_advertisers()
    assert len(advs) == 8
    pubs = load_publishers()
    assert len(pubs) == 5
    camps = load_campaigns()
    assert len(camps) == 20
    profile = load_traffic_profile()
    assert len(profile) == 24
    assert sum(profile.values()) == pytest.approx(100.0, 0.01)


def test_integration_full_engine_run():
    from services.engine import AdEngine
    engine = AdEngine()
    engine.open_day("2026-10-12")
    engine.process_until("2026-10-12 23:59:59")
    engine.close_day("2026-10-12")
    assert len(engine.auction_log_rows) > 0
    assert len(engine.daily_report_rows) == 20
