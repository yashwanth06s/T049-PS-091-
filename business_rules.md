# Digital Ad Auction, Budget Pacing and Frequency-Cap Engine
## Business Rules Register (PS-091) — Team T049

### Overview
This document registers all business rules (`BR-01` to `BR-12`), edge cases (`EC-01` to `EC-08`), and domain constraints for the ad-serving decision engine.

---

### Business Rules Register

#### BR-01: Eligibility & Targeting
- **Rule**: An ad campaign is eligible to participate in an auction for an ad request if and only if:
  1. The request matches all targeting dimensions: geographical location (`target_geos`), device type (`target_devices`), and category (`target_categories`). Targeting fields support semicolon-delimited lists or wildcard values (`ALL`, `*`, `ANY`).
  2. The request timestamp is strictly within the campaign's flight dates (`flight_start` 00:00:00 to `flight_end` 23:59:59 IST).
  3. The campaign's daily spend has not exhausted its daily budget (`spend_today < daily_budget`).
  4. The advertiser account is eligible:
     - `PREPAID`: Available wallet balance must be $\ge$ at least one max bid (`max_bid / 1000` for CPM, or `max_bid` for CPC).
     - `CREDIT`: Account must not be `SUSPENDED`.

#### BR-02: Frequency Capping
- **Rule**: Protects users from over-exposure:
  1. Maximum **3 impressions** per user per campaign per calendar day (IST).
  2. Maximum **1 impression** per user per campaign per clock hour (IST).
  3. Resets: Daily caps reset at 00:00:00 of each calendar day; hourly caps reset on each clock hour boundary.

#### BR-03: Bid Normalisation (Effective CPM / eCPM)
- **Rule**: Standardises bids across CPM and CPC models:
  - **CPM Bids**: $\text{eCPM} = \text{max\_bid}$
  - **CPC Bids**: $\text{eCPM} = \text{max\_bid} \times \text{trailing 7-day CTR} \times 1,000$
  - **Trailing CTR Calculation**:
    - Computed daily across the prior 7 calendar days ($D-7 \le \text{date} < D$) using historical data (`campaign_history.csv`) and impressions/valid clicks served in the run.
    - Default CTR: If total trailing impressions $< 1,000$, use default CTR of $0.5\%$ ($0.005$).
    - At $\ge 1,000$ impressions, switch immediately to actual CTR ($\frac{\text{valid\_clicks}}{\text{impressions}}$).

#### BR-04: Second-Price Auction & Floor Clearing
- **Rule**:
  1. If no participating campaign meets or exceeds the publisher's floor price (`eCPM < floor_price`): Result is `UNFILLED`, reason `"No bid meets the floor"`.
  2. If exactly **1 eligible bidder** meets/exceeds the floor: Winner pays exactly the `floor_price` (no increment).
  3. If **$\ge 2$ eligible bidders** participate:
     $$\text{Clearing CPM} = \max(\text{second-highest eCPM}, \text{publisher floor}) + \text{Rs } 0.01$$
     $$\text{Price per impression} = \frac{\text{Clearing CPM}}{1,000}$$

#### BR-05: Auction Tie-Breaking
- **Rule**: When two or more campaigns have identical highest eCPM:
  1. Winner is the campaign with the **lower cumulative spend today**.
  2. If still tied, winner is the campaign with the **lower campaign ID** (ascending alphanumeric order).

#### BR-06: Budget Pacing
- **Rule**: Daily budgets are distributed across 24 hourly buckets based on `traffic_profile.csv`:
  $$\text{Scheduled Budget through hour } H = \text{daily\_budget} \times \frac{\sum_{h=0}^H \text{pct}_h}{100}$$
  - **OVER_PACE**: `spend_today >= 120%` of cumulative scheduled budget through current hour.
  - **UNDER_PACE**: `spend_today < 100%` of cumulative scheduled budget.
  - **ON_PACE**: Between 100% and 120%.
  - **Catch-up mode**: When `UNDER_PACE`, campaign may spend up to $150\%$ of the current hour's bucket in that hour.

#### BR-07: Pacing Throttling
- **Rule**: When a campaign is `OVER_PACE`, it is throttled:
  - Participates only in every 2nd eligible request, determined deterministically by request sequence number parity:
    $$\text{request\_seq\_no} \pmod 2 == 0 \implies \text{Eligible to bid}$$
    $$\text{request\_seq\_no} \pmod 2 \ne 0 \implies \text{Sits out (Throttled)}$$
  - If a throttled campaign sits out and the request goes `UNFILLED`, `unfilled_due_to_throttle` is incremented.

#### BR-08: Billing Mechanics
- **Rule**:
  - **CPM Campaigns**: Billed immediately per served impression at $\frac{\text{Clearing CPM}}{1,000}$.
  - **CPC Campaigns**: Billed **only on click** at the CPC bid (`max_bid`), provided `spend_today < daily_budget` when the click arrives (capped so daily spend never exceeds daily budget by more than one bid).

#### BR-09: Wallet & Credit Limit Management
- **Rule**:
  - **Prepaid Accounts**: Spend debited from `wallet_balance`. Bidding ceases when wallet cannot afford one max bid.
  - **Credit Accounts**: Spend debited against credit line down to `-credit_limit`.
  - **Breach Rule**: A charge taking the balance below `-credit_limit` stands, and the advertiser is immediately marked `SUSPENDED`. Suspended advertisers cannot bid.

#### BR-10: Invalid Traffic (IVT) Detection & Clawback
- **Rule**:
  - A sliding window tracks clicks per `(user_id, campaign_id)`.
  - If $> 5$ clicks (i.e. $\ge 6$ clicks) arrive with $\text{click}_k - \text{click}_1 \le 10\text{ minutes}$ (600s):
    1. **All** clicks in that 10-minute window are marked `INVALID`.
    2. Advertiser billing for these clicks is reversed (refunded to wallet/credit balance).
    3. The publisher revenue share credited for these clicks is clawed back from publisher payout.

#### BR-11: Publisher Revenue Share & Payout Threshold
- **Rule**:
  - **Revenue Share Tiers**:
    - If total month-to-date billed $> \text{Rs } 1,00,000$: Revenue share is **70%**.
    - If $\le \text{Rs } 1,00,000$: Revenue share is **60%**.
  - **Clawback**: Deducted from payout due.
  - **Rollover**: If final net payout $< \text{Rs } 5,000$, payout is held and rolled over to the next month (`payout_due = 0.00`, `rolled_to_next = net_payout`).

#### BR-12: Flight End & Budget Expiry
- **Rule**:
  - Campaigns serve until 23:59:59 on `flight_end`.
  - Unspent daily budget or campaign budget lapses and **never carries forward**.

---

### Planted Edge Cases (EC-01 to EC-08)

| Code | Scenario | Expected Behavior | Verification |
|---|---|---|---|
| **EC-01** | Single bidder equals floor exactly | Single bidder pays publisher floor exactly (no increment). | Verified in `REQ-000466` on PUB-5 (Rs 150.00 CPM). |
| **EC-02** | 2nd-highest bid below floor | Winner pays $\max(\text{2nd bid}, \text{floor}) + 0.01 = \text{floor} + 0.01$. | Verified in `REQ-000171` on PUB-4 (Rs 120.01 CPM). |
| **EC-03** | Exactly 1,000 trailing impressions | Switches from default 0.5% CTR to actual CTR ($7/1000 = 0.7\%$). | Verified in `CMP-006` on `REQ-000087` (eCPM 175.00). |
| **EC-04** | Pacing at 120.0% boundary | Campaign marks `OVER_PACE`, sits out on odd sequence `REQ-000519`. | Verified in `CMP-001` (`ThrottledUnfilled = 1`). |
| **EC-05** | Frequency cap day/hour boundary | 3rd impression served at 23:59:00, 23:59:30 blocked, 00:00:00 next day served. | Verified in `REQ-000463`, `REQ-000464`, `REQ-000465`. |
| **EC-06** | 6th click arriving within 10:00 | All 6 clicks marked INVALID, billing reversed, Rs 90 clawback on PUB-4. | Verified in `CLK-00057..CLK-00062` on CMP-006. |
| **EC-07** | Publisher at exactly Rs 1,00,000 | Exactly 100,000 is not *above* 100,000 -> 60% revenue share tier. | Verified in `PUB-5` ($99982.60 + 17.40 = 100000.00$). |
| **EC-08** | Credit advertiser breach by Rs 0.01 | Winning bid takes balance to -50,000.01 -> charge stands, suspended. | Verified in `ADV-07` on `REQ-001079`, 12 later stay unfilled. |
