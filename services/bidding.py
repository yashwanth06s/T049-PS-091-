from decimal import Decimal


DEFAULT_CTR = Decimal("0.005")


def validate_bid(campaign):
    if campaign.bid_type not in ("CPM", "CPC"):
        raise ValueError(f"Invalid bid type: {campaign.bid_type}")
    if campaign.max_bid <= 0:
        raise ValueError("Bid amount must be positive")
    return True


def calculate_ctr(impressions, valid_clicks):
    """
    Computes trailing CTR per BR-03 and EC-03:
    Default 0.5% (0.005) if fewer than 1,000 impressions.
    At exactly 1,000 impressions or more, switch to actual CTR: valid_clicks / impressions.
    """
    if impressions < 1000:
        return DEFAULT_CTR
    if impressions == 0:
        return DEFAULT_CTR
    return Decimal(str(valid_clicks)) / Decimal(str(impressions))


def calculate_ecpm(campaign, trailing_ctr=DEFAULT_CTR):
    """
    Normalises bids to eCPM per BR-03:
    - CPM bids: eCPM = max_bid
    - CPC bids: eCPM = max_bid * trailing_ctr * 1000
    """
    validate_bid(campaign)
    max_bid = Decimal(str(campaign.max_bid))
    if campaign.bid_type == "CPM":
        return max_bid
    elif campaign.bid_type == "CPC":
        ctr = Decimal(str(trailing_ctr))
        return max_bid * ctr * Decimal("1000")
    else:
        raise ValueError(f"Unsupported bid type: {campaign.bid_type}")
