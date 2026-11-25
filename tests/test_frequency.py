"""
Unit tests for BR-02: Frequency Capping and EC-05: Day/Hour Frequency Boundaries.
Author: Yashaswini (Team T049)
"""

from datetime import date, datetime
import pytest
from models.campaign import Campaign
from services.frequency_service import FrequencyService


@pytest.fixture
def test_campaign():
    return Campaign(
        campaign_id="CMP-TEST-FREQ",
        advertiser_id="ADV-01",
        flight_start=date(2026, 10, 1),
        flight_end=date(2026, 10, 31),
        daily_budget=2000.0,
        bid_type="CPM",
        max_bid=80.0,
        target_geos=["ALL"],
        target_devices=["ALL"],
        target_categories=["ALL"],
        freq_cap_day=3,
        freq_cap_hour=1
    )


def test_frequency_hourly_cap_blocks_second_impression(test_campaign):
    fs = FrequencyService()
    user = "U_FREQ_01"
    req_date = date(2026, 10, 12)
    hour = 14

    # First impression in hour 14 is allowed
    assert fs.can_serve(test_campaign, user, req_date, hour) is True
    fs.record_impression(test_campaign.campaign_id, user, req_date, hour)

    # Second impression in the same clock hour 14 must be blocked (BR-02)
    assert fs.can_serve(test_campaign, user, req_date, hour) is False


def test_frequency_hourly_cap_resets_on_next_clock_hour(test_campaign):
    fs = FrequencyService()
    user = "U_FREQ_02"
    req_date = date(2026, 10, 12)

    # Hour 9: 1st impression served
    assert fs.can_serve(test_campaign, user, req_date, 9) is True
    fs.record_impression(test_campaign.campaign_id, user, req_date, 9)
    assert fs.can_serve(test_campaign, user, req_date, 9) is False

    # Hour 10: new clock hour resets the hourly cap
    assert fs.can_serve(test_campaign, user, req_date, 10) is True
    fs.record_impression(test_campaign.campaign_id, user, req_date, 10)
    assert fs.can_serve(test_campaign, user, req_date, 10) is False

    # Hour 11: 3rd impression across the day
    assert fs.can_serve(test_campaign, user, req_date, 11) is True
    fs.record_impression(test_campaign.campaign_id, user, req_date, 11)
    assert fs.can_serve(test_campaign, user, req_date, 11) is False


def test_frequency_daily_cap_blocks_fourth_impression(test_campaign):
    fs = FrequencyService()
    user = "U_FREQ_03"
    req_date = date(2026, 10, 12)

    # Deliver 3 impressions in hours 8, 9, 10 (allowed by hourly cap of 1)
    for hr in [8, 9, 10]:
        assert fs.can_serve(test_campaign, user, req_date, hr) is True
        fs.record_impression(test_campaign.campaign_id, user, req_date, hr)

    # In hour 11, hourly cap is 0, but daily cap of 3 has been reached
    assert fs.can_serve(test_campaign, user, req_date, 11) is False
    day_cnt, hr_cnt = fs.get_counts(test_campaign.campaign_id, user, req_date, 11)
    assert day_cnt == 3
    assert hr_cnt == 0


def test_frequency_daily_cap_resets_at_midnight_ist(test_campaign):
    fs = FrequencyService()
    user = "U_FREQ_04"
    day_1 = date(2026, 10, 12)
    day_2 = date(2026, 10, 13)

    # Reach 3 impressions on day_1 (at hours 21, 22, 23)
    for hr in [21, 22, 23]:
        assert fs.can_serve(test_campaign, user, day_1, hr) is True
        fs.record_impression(test_campaign.campaign_id, user, day_1, hr)

    # 4th attempt on day_1 at hour 23 is blocked
    assert fs.can_serve(test_campaign, user, day_1, 23) is False

    # On day_2 at 00:00:00 (hour 0), daily cap resets
    assert fs.can_serve(test_campaign, user, day_2, 0) is True
    fs.record_impression(test_campaign.campaign_id, user, day_2, 0)
    day_cnt, hr_cnt = fs.get_counts(test_campaign.campaign_id, user, day_2, 0)
    assert day_cnt == 1
    assert hr_cnt == 1


def test_frequency_multi_user_isolation(test_campaign):
    fs = FrequencyService()
    req_date = date(2026, 10, 12)
    hour = 12

    # User 1 exhausts hourly cap
    fs.record_impression(test_campaign.campaign_id, "USER_A", req_date, hour)
    assert fs.can_serve(test_campaign, "USER_A", req_date, hour) is False

    # User 2 must still be eligible
    assert fs.can_serve(test_campaign, "USER_B", req_date, hour) is True


def test_frequency_multi_campaign_isolation(test_campaign):
    fs = FrequencyService()
    campaign_2 = Campaign(
        campaign_id="CMP-TEST-FREQ-2",
        advertiser_id="ADV-02",
        flight_start=date(2026, 10, 1),
        flight_end=date(2026, 10, 31),
        daily_budget=1500.0,
        bid_type="CPM",
        max_bid=60.0,
        target_geos=["ALL"],
        target_devices=["ALL"],
        target_categories=["ALL"],
        freq_cap_day=3,
        freq_cap_hour=1
    )
    user = "USER_SHARED"
    req_date = date(2026, 10, 12)
    hour = 15

    # Exhaust cap on Campaign 1
    fs.record_impression(test_campaign.campaign_id, user, req_date, hour)
    assert fs.can_serve(test_campaign, user, req_date, hour) is False

    # Campaign 2 must remain eligible for the same user in the same hour
    assert fs.can_serve(campaign_2, user, req_date, hour) is True
