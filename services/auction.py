from decimal import Decimal


def run_second_price_auction(candidates, floor_price):
    """
    Runs a second-price advertisement auction adhering to BR-04, BR-05, EC-01, and EC-02.

    Parameters:
        candidates: List of dicts, each with:
            - "campaign_id": str
            - "campaign": Campaign object
            - "ecpm": Decimal
            - "spend_today": Decimal
        floor_price: Decimal or float/str representing the publisher's floor CPM.

    Returns:
        Dict representing auction outcome.
    """
    floor = Decimal(str(floor_price))

    if not candidates:
        return {
            "outcome": "UNFILLED",
            "winner_campaign_id": "",
            "winner_campaign": None,
            "winner_ecpm": "",
            "second_ecpm": "",
            "clearing_cpm": "",
            "price_per_impression": Decimal("0.00"),
            "bidders": 0,
            "reason": "No eligible campaigns"
        }

    # Sort all participating candidates:
    # 1. Highest eCPM (descending)
    # 2. Lower cumulative spend today (ascending, BR-05 tie breaker)
    # 3. Campaign ID ascending (BR-05 tie breaker)
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (
            -Decimal(str(c["ecpm"])),
            Decimal(str(c["spend_today"])),
            str(c["campaign_id"])
        )
    )

    # Check if highest bid meets floor
    winner = sorted_candidates[0]
    winner_ecpm = Decimal(str(winner["ecpm"]))

    if winner_ecpm < floor:
        return {
            "outcome": "UNFILLED",
            "winner_campaign_id": "",
            "winner_campaign": None,
            "winner_ecpm": "",
            "second_ecpm": "",
            "clearing_cpm": "",
            "price_per_impression": Decimal("0.00"),
            "bidders": len(candidates),
            "reason": "No bid meets the floor"
        }

    # Second-price clearing logic
    if len(sorted_candidates) == 1:
        # EC-01: Single bidder whose bid meets or exceeds the floor pays the floor
        clearing_cpm = floor
        second_ecpm_str = ""
    else:
        # Multiple bidders: winner pays max(second-highest eCPM, publisher floor) + Rs 0.01
        # EC-02: Second-highest bid below floor -> winner pays floor + 0.01
        second_bidder = sorted_candidates[1]
        second_ecpm = Decimal(str(second_bidder["ecpm"]))
        clearing_cpm = max(second_ecpm, floor) + Decimal("0.01")
        second_ecpm_str = f"{second_ecpm:.2f}"

    price_per_impression = clearing_cpm / Decimal("1000")

    return {
        "outcome": "SERVED",
        "winner_campaign_id": winner["campaign_id"],
        "winner_campaign": winner["campaign"],
        "winner_ecpm": f"{winner_ecpm:.2f}",
        "second_ecpm": second_ecpm_str,
        "clearing_cpm": f"{clearing_cpm:.2f}",
        "price_per_impression": price_per_impression,
        "bidders": len(candidates),
        "reason": "Highest eligible bid won"
    }
