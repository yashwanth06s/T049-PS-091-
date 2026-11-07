# Digital Ad Auction, Budget Pacing and Frequency-Cap Engine (PS-091)
### Team: T049 | Domain: Media - AdTech | Tech Stack: Python 3.10+

### Team Members:
- **Yashwanth S** ([@yashwanth06s](https://github.com/yashwanth06s)) — Decision Engine, Second-Price Auction & Budget Pacing
- **Yashaswini** ([@yashaswini3135](https://github.com/yashaswini3135)) — Frequency Capping, IVT Detection & Test Suite

## 1. Project Overview
This project implements a command-file driven **Ad-Serving Decision Engine** built for a digital publisher network. The engine:
- Ingests advertiser wallets, campaign parameters, publisher floor prices, and hourly traffic distribution profiles.
- Processes continuous ad requests and click event streams merged chronologically in IST.
- Executes second-price auctions with floor prices and deterministic tie-breaking.
- Controls budget pacing across 24 hourly buckets with automatic parity throttling and catch-up spending.
- Enforces strict user frequency caps per calendar day and clock hour.
- Bills CPM campaigns on impressions and CPC campaigns on clicks with daily budget caps.
- Detects Invalid Traffic (IVT) using a 10-minute rolling window and claws back publisher revenue share.
- Produces daily campaign reports and publisher revenue settlements.

---

## 2. Project Architecture & Structure

```text
T049-PS-091/
├── README.md                  # Project overview, setup, and viva guide
├── business_rules.md          # Formal register for BR-01 to BR-12 and EC-01 to EC-08
├── decision_log.md            # Technical decisions and trade-offs log
├── requirements.txt           # Test dependencies (pytest)
├── main.py                    # CLI application entry point (processes commands.txt)
├── data/                      # Input dataset (CSVs, commands.txt, traffic_profile.csv)
├── models/                    # Validated data models
│   ├── advertiser.py          # Advertiser dataclass (prepaid/credit accounts)
│   ├── campaign.py            # Campaign dataclass (targeting, flight, budgets)
│   └── publisher.py           # Publisher dataclass (floor price, rev share)
├── services/                  # Core domain logic
│   ├── auction.py             # BR-04, BR-05 (Second-price auction, floor clearing, ties)
│   ├── bidding.py             # BR-03 (eCPM calculation, trailing 7-day CTR)
│   ├── budget_service.py      # BR-06, BR-07 (Hourly budget pacing, parity throttling)
│   ├── billing_service.py     # BR-08, BR-09, BR-11 (Billing, credit limits, payouts)
│   ├── frequency_service.py   # BR-02 (User daily & hourly frequency caps)
│   ├── click_service.py       # BR-10 (IVT detection, rolling 10-min window)
│   ├── eligibility.py         # BR-01 (Targeting, dates, budget, wallet checks)
│   ├── data_loader.py         # CSV parsing into typed data structures
│   ├── report_service.py      # Formatted CSV report generators
│   └── engine.py              # Master simulation and event pipeline
├── output/                    # Generated evaluation CSV deliverables
│   ├── auction_log.csv
│   ├── click_log.csv
│   ├── daily_campaign_report.csv
│   └── publisher_payout.csv
└── tests/                     # 40+ automated unit tests
    ├── test_br01_to_br12.py   # Explicit unit tests for BR-01 to BR-12
    ├── test_edge_cases.py     # Verification tests for all 8 planted edge cases (EC-01..EC-08)
    └── test_models_and_services.py # Data validations and service tests
```

---

## 3. How to Run the Application

The engine requires **Python 3.10+** (developed and tested on Python 3.13) and has **zero external runtime dependencies**.

### Run Simulation
```bash
python main.py data/commands.txt
```
Or simply:
```bash
python main.py
```

Outputs will be printed to stdout and saved directly to the `output/` directory as well as the root project directory:
1. `output/auction_log.csv`
2. `output/click_log.csv`
3. `output/daily_campaign_report.csv`
4. `output/publisher_payout.csv`

---

## 4. How to Run Automated Tests

To execute the full test suite (40 tests):
```bash
python -m pytest tests -v
```

All 40 tests validate every individual business rule, planted edge case, and data model constraint.

---

## 5. Verification of All 8 Planted Edge Cases

- **EC-01 (Single Bidder Equals Floor)**: In `REQ-000466` on `PUB-5` (floor Rs 150.00), only `CMP-001` is eligible. As a single bidder, it pays exactly the floor price (Rs 0.15/impression).
- **EC-02 (Second Bidder Below Floor)**: In `REQ-000171` on `PUB-4` (floor 120.00), `CMP-004` bids 180.00 and `CMP-005` bids 90.00. Winner `CMP-004` pays $\max(90.00, 120.00) + 0.01 = \text{Rs } 120.01\text{ CPM}$.
- **EC-03 (1,000 Trailing Impressions Switch)**: `CMP-006` has exactly 1,000 trailing impressions and 7 valid clicks in `campaign_history.csv` -> switches from default 0.5% CTR to actual 0.7% CTR ($\text{eCPM} = 25 \times 0.007 \times 1000 = 175.00$).
- **EC-04 (120% Pacing Boundary)**: `CMP-001` reaches 120.0% of cumulative scheduled budget at hour 0. It is marked `OVER_PACE`, sits out on odd request `REQ-000519` (`ThrottledUnfilled = 1`), and resumes bidding at `REQ-000520` (hour 1).
- **EC-05 (Frequency Cap Day/Hour Boundary)**: `U77770001` receives 3rd impression on `CMP-002` at 23:59:00 (`REQ-000463`). Request at 23:59:30 is capped. Request at 00:00:00 next day (`REQ-000465`) serves successfully.
- **EC-06 (IVT 10-Minute Window)**: Clicks `CLK-00057..CLK-00062` on `CMP-006` arrive within 10 minutes. All 6 clicks are marked `INVALID`, CPC charges refunded, and Rs 90.00 ($150 \times 60\%$) clawed back from `PUB-4`.
- **EC-07 (Publisher at Exactly Rs 1,00,000)**: `PUB-5` reaches exactly Rs 1,00,000.00 ($99982.60 + 17.40$). Because it is not *above* 1,00,000, it stays at the **60%** revenue share tier.
- **EC-08 (Credit Advertiser Limit Breach)**: Winning `REQ-001079` costs Rs 0.15, taking `ADV-07` balance to -50,000.01 (Rs 0.01 beyond credit limit). The charge stands and `ADV-07` is `SUSPENDED`; its 12 subsequent spiritual requests remain `UNFILLED`.

---

## 6. Viva Cheat Sheet & Key Concepts

1. **Second-Price Clearing with Floors**:
   - Single bidder pays the floor price directly.
   - Multiple bidders pay $\max(\text{second-highest eCPM}, \text{publisher floor}) + 0.01$.
2. **Pacing & Parity Throttling**:
   - `OVER_PACE` ($> 120\%$): Drops odd request sequences (`seq_no % 2 != 0`).
   - `UNDER_PACE` ($< 100\%$): Catch-up spending allowed up to $150\%$ of current hour's bucket.
3. **Credit Accounts**:
   - Can operate in negative balance down to `-credit_limit`.
   - Any transaction breaching the limit stands and suspends the account immediately.

