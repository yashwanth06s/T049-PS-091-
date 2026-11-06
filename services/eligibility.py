from datetime import date, datetime
from decimal import Decimal


def _to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _matches(target_values, request_value):
    if isinstance(target_values, str):
        target_values = [v.strip() for v in target_values.split(";")]
    elif isinstance(target_values, (list, tuple, set)):
        target_values = [str(v).strip() for v in target_values]
    else:
        target_values = [str(target_values).strip()]

    request_value = str(request_value).strip().upper()
    return any(
        v.upper() in ("ALL", "*", "ANY", request_value)
        for v in target_values
    )


def check_eligibility(
    campaign,
    advertiser,
    request_geo,
    request_device,
    request_category,
    request_ts,
    daily_spend,
    user_day_impressions=0,
    user_hour_impressions=0
):
    """
    Checks BR-01, BR-02 eligibility requirements:
    1. Targeting match: geo, device, category
    2. Flight date range: flight_start <= request_date <= flight_end (23:59:59)
    3. Daily budget not exhausted: daily_spend < daily_budget
    4. Advertiser status:
       - Credit: non-suspended
       - Prepaid: wallet_balance >= 1 max bid (CPM: max_bid / 1000, CPC: max_bid)
    5. Frequency caps:
       - user impressions today < freq_cap_day
       - user impressions this hour < freq_cap_hour
    """
    reasons = []

    # 1. Targeting
    if not _matches(campaign.target_geos, request_geo):
        reasons.append("Geographical targeting mismatch")

    if not _matches(campaign.target_devices, request_device):
        reasons.append("Device targeting mismatch")

    if not _matches(campaign.target_categories, request_category):
        reasons.append("Category targeting mismatch")

    # 2. Flight dates
    req_date = _to_date(request_ts)
    if req_date < _to_date(campaign.flight_start):
        reasons.append("Campaign flight has not started")
    if req_date > _to_date(campaign.flight_end):
        reasons.append("Campaign flight has ended")

    # 3. Daily budget
    if Decimal(str(daily_spend)) >= Decimal(str(campaign.daily_budget)):
        reasons.append("Daily budget exhausted")

    # 4. Advertiser wallet / credit limit
    if advertiser.suspended:
        reasons.append("Advertiser credit account is suspended")
    else:
        min_required_balance = (
            Decimal(str(campaign.max_bid)) / Decimal("1000")
            if campaign.bid_type == "CPM"
            else Decimal(str(campaign.max_bid))
        )
        if advertiser.account_type == "PREPAID":
            if Decimal(str(advertiser.wallet_balance)) < min_required_balance:
                reasons.append("Insufficient prepaid wallet balance for one max bid")

    # 5. Frequency caps
    if user_day_impressions >= campaign.freq_cap_day:
        reasons.append("Daily frequency cap reached for user")
    if user_hour_impressions >= campaign.freq_cap_hour:
        reasons.append("Hourly frequency cap reached for user")

    return len(reasons) == 0, reasons
