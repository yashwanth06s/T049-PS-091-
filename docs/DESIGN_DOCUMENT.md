# CAPSTONE PROJECT DESIGN DOCUMENT
## PS-091: Digital Ad Auction, Budget Pacing and Frequency-Cap Engine
**Team ID**: T049  
**Team Members**: Yashwanth S ([@yashwanth06s](https://github.com/yashwanth06s)) & Yashaswini ([@yashaswini3135](https://github.com/yashaswini3135))  
**Domain**: Media - AdTech | **Language**: Python 3.10+ (Tested on Python 3.13)  
**Submission Milestone**: Week 1 Design Document (Updated for Final Review)

---

## 1. Domain Glossary

| Term | Definition & Domain Significance |
|---|---|
| **Publisher** | The digital property (website/app) supplying ad inventory slots (e.g. news portal, sports app). Sets a minimum floor price. |
| **Advertiser** | The brand purchasing ad space to promote products. Holds either a prepaid wallet or a credit facility account. |
| **Campaign** | An advertising initiative configured with flight dates, daily budget, targeting criteria, bid model, and frequency caps. |
| **CPM (Cost Per Mille)** | Cost per 1,000 ad impressions (views). CPM campaigns are billed immediately upon impression delivery. |
| **CPC (Cost Per Click)** | Pricing model where advertisers are billed only when a verified user clicks on a served ad. |
| **eCPM (Effective CPM)** | The normalized revenue per 1,000 impressions used to compare CPC and CPM bids on an equal footing: $eCPM = CPC \times CTR \times 1000$. |
| **CTR (Click-Through Rate)** | The ratio of valid clicks to impressions: $CTR = \frac{\text{Clicks}}{\text{Impressions}}$. Trailing 7-day window used for CPC normalisation. |
| **Floor Price** | The reserve CPM price set by a publisher. No ad request can clear below this price. |
| **Second-Price Auction** | Auction mechanism where the highest eligible bidder wins, but clears at $\max(\text{2nd-highest eCPM}, \text{Floor}) + \text{Rs } 0.01$. Single bidders clear at the Floor. |
| **Frequency Cap** | Rules restricting user ad fatigue: max 3 impressions per user per calendar day (IST) and max 1 per user per clock hour. |
| **Budget Pacing** | Strategy spreading daily spend across 24 hourly buckets according to an empirical traffic distribution profile. |
| **Parity Throttling** | Deterministic mechanism that forces an over-pace campaign to sit out of odd-sequence requests ($seq\_no \% 2 \ne 0$). |
| **Catch-Up Spending** | Allows an under-spent campaign to consume up to 150% of the current hour's allocated bucket. |
| **Invalid Traffic (IVT)** | Fraudulent or burst clicks: $> 5$ clicks from the same user on the same campaign within a rolling 10-minute window. |
| **Revenue Share Clawback** | Reversal of publisher credits resulting from invalidated clicks, recovered from the publisher's subsequent payout. |
| **Payout Rollover** | If a publisher's monthly payout is below Rs 5,000, disbursement is deferred and rolls over to the following month. |

---

## 2. System Architecture & Class Diagram

```mermaid
classDiagram
    class Advertiser {
        +str advertiser_id
        +str name
        +str account_type
        +float wallet_balance
        +float credit_limit
        +bool suspended
    }

    class Publisher {
        +str publisher_id
        +str name
        +float floor_price
        +float monthly_billed_amount
        +float rollover_payout
        +int revenue_share
    }

    class Campaign {
        +str campaign_id
        +str advertiser_id
        +date flight_start
        +date flight_end
        +float daily_budget
        +str bid_type
        +float max_bid
        +list target_geos
        +list target_devices
        +list target_categories
        +int freq_cap_day
        +int freq_cap_hour
    }

    class AdRequest {
        +str request_id
        +datetime request_ts
        +str publisher_id
        +str user_id
        +str geo
        +str device
        +str category
    }

    class Click {
        +str click_id
        +str request_id
        +str user_id
        +datetime click_ts
    }

    class AdEngine {
        +dict advertisers
        +dict publishers
        +dict campaigns
        +list event_queue
        +open_day(date_str)
        +process_until(ts_str)
        +close_day(date_str)
    }

    class BudgetService {
        +dict traffic_profile
        +dict daily_spend
        +dict hourly_spend
        +get_pacing_status()
        +can_bid()
        +record_spend()
        +refund_spend()
    }

    class FrequencyService {
        +dict daily_counts
        +dict hourly_counts
        +can_serve()
        +record_impression()
    }

    class ClickService {
        +list clicks
        +dict user_campaign_clicks
        +process_click()
    }

    class BillingService {
        +dict publisher_mtd_billed
        +dict publisher_clawbacks
        +charge_impression()
        +charge_click()
        +reverse_click()
        +get_publisher_payout()
    }

    AdEngine --> Advertiser
    AdEngine --> Publisher
    AdEngine --> Campaign
    AdEngine --> BudgetService
    AdEngine --> FrequencyService
    AdEngine --> ClickService
    AdEngine --> BillingService
```

---

## 3. State Machine Diagrams

### 3.1 Ad Request Lifecycle & Auction Pipeline
```mermaid
stateDiagram-v2
    [*] --> RequestReceived: AdRequest Arrives
    RequestReceived --> TargetingFilter: Match Geo, Device, Category
    TargetingFilter --> FlightDateFilter: Check Flight Start & End
    FlightDateFilter --> AccountCheck: Verify Wallet / Credit Non-Suspended
    AccountCheck --> FrequencyCapCheck: User Day <= 3 & Hour <= 1
    FrequencyCapCheck --> PacingFilter: Check 120% Spend & Seq Parity
    PacingFilter --> EligiblePool: Campaign Enters Auction
    PacingFilter --> ThrottledOut: Odd Seq in OVER_PACE (Sits Out)
    EligiblePool --> FloorCheck: Compare eCPM against Floor
    FloorCheck --> Unfilled: No Bid >= Floor
    FloorCheck --> SecondPriceCleared: Winner Clears at Max(2nd, Floor) + 0.01
    SecondPriceCleared --> BillingStage: CPM Debited Immediately
    BillingStage --> ImpressionLogged: Frequency Recorded
    ImpressionLogged --> [*]
    Unfilled --> [*]
```

### 3.2 Campaign Budget Pacing State Machine
```mermaid
stateDiagram-v2
    [*] --> ON_PACE: Spend between 100% and 120% of Schedule
    ON_PACE --> OVER_PACE: Spend >= 120% of Cumulative Schedule
    OVER_PACE --> ON_PACE: New Hour Extends Schedule Budget
    OVER_PACE --> Throttled: Odd Request Sequence (Sits Out)
    OVER_PACE --> Participates: Even Request Sequence
    ON_PACE --> UNDER_PACE: Spend < 100% of Cumulative Schedule
    UNDER_PACE --> ON_PACE: Spend Catches Up (Max 150% of Hour Bucket)
```

### 3.3 Advertiser Account State Machine
```mermaid
stateDiagram-v2
    [*] --> ActivePrepaid: AccountType == PREPAID
    [*] --> ActiveCredit: AccountType == CREDIT
    ActivePrepaid --> Exhausted: Balance < 1 Max Bid (Bidding Paused)
    Exhausted --> ActivePrepaid: Wallet Reloaded
    ActiveCredit --> ActiveCredit: Balance >= -CreditLimit
    ActiveCredit --> Suspended: Balance < -CreditLimit (Breach Stands)
    Suspended --> [*]: Bidding Permanently Ceased
```

---

## 4. Complete Business Rules Register (BR-01 to BR-12)

### BR-01: Targeting & Flight Date Eligibility
- **Condition**: Request matches `target_geos`, `target_devices`, `target_categories`. Request timestamp within `flight_start` 00:00:00 and `flight_end` 23:59:59.
- **Budget & Wallet Condition**: `spend_today < daily_budget`. Prepaid wallet $\ge 	ext{max\_bid}/1000$ (CPM) or $\ge 	ext{max\_bid}$ (CPC). Credit account non-suspended.

### BR-02: User Frequency Capping
- **Condition**: Per user ID per campaign in IST: Maximum **3 impressions/day** and **1 impression/hour**. Resets on day boundary (00:00:00) and clock hour boundaries.

### BR-03: Bid Normalisation & Trailing CTR
- **Formulas**:
  - CPM: $	ext{eCPM} = 	ext{max\_bid}$
  - CPC: $	ext{eCPM} = 	ext{max\_bid} 	imes 	ext{trailing\_ctr} 	imes 1,000$
  - Trailing CTR: Computed over prior 7 calendar days ($D-7 \le 	ext{date} < D$). Default = 0.5% (0.005) if trailing impressions $< 1,000$. At $\ge 1,000$, switches to actual CTR.

### BR-04: Second-Price Auction & Floor Clearing
- **Formulas**:
  - No bids $\ge 	ext{Floor} \implies 	ext{UNFILLED}$.
  - Single eligible bidder $\ge 	ext{Floor} \implies 	ext{Clearing CPM} = 	ext{Floor}$.
  - $\ge 2$ bidders $\implies 	ext{Clearing CPM} = \max(	ext{second-highest eCPM}, 	ext{Floor}) + 	ext{Rs } 0.01$.
  - Charge per impression: $rac{	ext{Clearing CPM}}{1000}$.

### BR-05: Auction Tie-Breaking
- **Precedence**:
  1. Lower cumulative spend today.
  2. Lower campaign ID (ascending alphanumeric sort).

### BR-06: Budget Pacing & Catch-Up Mode
- **Formulas**:
  - Cumulative scheduled budget up to current hour $H = 	ext{budget} 	imes \sum_{h=0}^H rac{	ext{pct}_h}{100}$.
  - $	ext{OVER\_PACE}$ if $	ext{spend} \ge 1.20 	imes 	ext{scheduled}$.
  - $	ext{UNDER\_PACE}$ if $	ext{spend} < 	ext{scheduled}$.
  - In catch-up mode, max hourly spend allowed $= 1.50 	imes 	ext{hour\_bucket}$.

### BR-07: Pacing Parity Throttling
- **Rule**: When `OVER_PACE`, campaign bids only on even request sequence numbers (`seq_no % 2 == 0`). Sits out on odd sequence numbers (`seq_no % 2 != 0`).

### BR-08: Billing Mechanics
- **Rules**:
  - CPM billed immediately on impression at clearing price.
  - CPC billed on click at `max_bid`, only if `spend_today < daily_budget` when click arrives.

### BR-09: Wallet & Credit Limit Management
- **Rules**:
  - Prepaid debits wallet down to 0.00.
  - Credit debits line down to `-credit_limit`. Any charge breaching limit stands and suspends the advertiser.

### BR-10: Invalid Traffic (IVT) Detection & Clawback
- **Rules**:
  - $> 5$ clicks from same user on same campaign within 10 minutes (600s) $\implies$ all clicks in window marked `INVALID`.
  - Advertiser refunded CPC charge.
  - Publisher revenue share clawed back from monthly payout.

### BR-11: Publisher Revenue Share & Payout Threshold
- **Rules**:
  - Total month-to-date billed $> 	ext{Rs } 1,00,000 \implies 70\%$ rev share.
  - $\le 	ext{Rs } 1,00,000 \implies 60\%$ rev share.
  - If payout due $< 	ext{Rs } 5,000$, rolls to next month (`payout_due = 0.00`).

### BR-12: Flight End & Budget Expiry
- **Rules**:
  - Flight serves until 23:59:59 on end date.
  - Unspent daily budget lapses at 23:59:59 and never carries forward.

---

## 5. Planted Edge Cases Verification Table

| ID | Edge Case | Observed System Output | Result |
|---|---|---|---|
| **EC-01** | Single bidder equals floor | REQ-000466: CMP-001 bids 150.00 = floor 150.00 $ightarrow$ clears at 150.00 (Rs 0.15/imp) | Passed |
| **EC-02** | 2nd bid below floor | REQ-000171: CMP-004 (180.00) vs CMP-005 (90.00) on PUB-4 (120.00) $ightarrow$ clears at 120.01 | Passed |
| **EC-03** | 1,000 trailing impressions | CMP-006 switches from 0.5% to 0.7% CTR on 2026-10-12 $ightarrow$ eCPM 175.00 (REQ-000087) | Passed |
| **EC-04** | Pacing at 120.0% boundary | CMP-001 throttled on odd REQ-000519 (`ThrottledUnfilled = 1`), wins REQ-000520 at hour 1 | Passed |
| **EC-05** | Day/hour frequency boundary | REQ-000463 served (3rd today), REQ-000464 capped, REQ-000465 served at 00:00:00 next day | Passed |
| **EC-06** | 6th click within 10:00 | CLK-00057..62 on CMP-006 marked INVALID; Rs 90.00 clawed back from PUB-4 | Passed |
| **EC-07** | Publisher exactly Rs 1,00,000 | PUB-5 October total = Rs 100,000.00 $ightarrow$ evaluated at 60% revenue share tier | Passed |
| **EC-08** | Credit breach by Rs 0.01 | ADV-07 balance hits -50,000.01 on REQ-001079 $ightarrow$ suspended; 12 later spiritual stay unfilled | Passed |
