# 5-Minute Demo Video Script & Walkthrough Guide
## PS-091: Digital Ad Auction, Budget Pacing and Frequency-Cap Engine
**Team ID**: T049 | **Domain**: Media - AdTech  
**Team Members**: Yashwanth S ([@yashwanth06s](https://github.com/yashwanth06s)) & Yashaswini ([@yashaswini3135](https://github.com/yashaswini3135))  
**Placement Coaching Capstone Project** — 10 SECONDS

---

## Video Specifications & Recording Checklist
- **Duration**: Exactly 4:45 to 5:00 minutes (Strict adherence to the 5-minute cap).
- **Resolution**: 1080p (1920x1080), 30 or 60 fps.
- **Audio**: Clear microphone input; quiet background.
- **Screen Layout**:
  - Split screen or full-screen terminal with high contrast (font size 16pt+).
  - VS Code / IDE displaying project structure and key code files.
  - CSV viewer / spreadsheet or terminal head outputs for generated reports.

---

## Minute-by-Minute Presentation Timeline

| Time Window | Speaker | Focus Area | Visual on Screen |
|---|---|---|---|
| **0:00 – 0:45** | Yashwanth S | Introduction, Problem Statement, & Scope | Title slide, GitHub repository overview, Team T049 intro |
| **0:45 – 1:45** | Yashaswini | System Architecture, Data Flow, & Models | VS Code project tree, Mermaid class diagram, `services/` modules |
| **1:45 – 3:00** | Yashwanth S | Live Simulation Run & Output Deliverables | Terminal executing `python main.py data/commands.txt`, CSV outputs |
| **3:00 – 4:00** | Yashaswini | Planted Edge Cases Deep Dive (EC-01..EC-08) | Highlighting specific log rows in `auction_log.csv` and `click_log.csv` |
| **4:00 – 4:45** | Yashwanth S | Automated Test Suite (50 Unit Tests) | Running `python -m pytest tests -v` with 100% green pass rate |
| **4:45 – 5:00** | Both | Conclusion & Viva Readiness | Final summary slide / GitHub repo README |

---

## Word-for-Word Presentation Script

### [0:00 - 0:45] Introduction & Problem Statement
**Visual**: Show project repository root on GitHub / VS Code with `README.md`.

**Yashwanth S**:
> "Hello everyone. We are Team T049, representing the Media and AdTech domain for the 10 SECONDS Capstone Project. I am Yashwanth S, and joining me is my teammate Yashaswini.
> 
> Our problem statement is **PS-091: Digital Ad Auction, Budget Pacing, and Frequency-Cap Engine**.
> 
> In modern programmatic advertising, ad exchanges must process high-frequency ad requests and click streams in real time. Our goal was to build a deterministic, high-precision decision engine in Python that executes second-price auctions with publisher reserve floors, regulates advertiser budget pacing across 24 hourly buckets, enforces strict per-user frequency caps, detects Invalid Traffic using sliding time windows, and generates publisher payout settlements with tier-based revenue sharing and rollovers."

---

### [0:45 - 1:45] System Architecture & Modular Design
**Visual**: Expand project directories in VS Code: `models/`, `services/`, `data/`, `tests/`.

**Yashaswini**:
> "To deliver a production-grade architecture, we developed the system with zero runtime external dependencies, leveraging Python's standard library and fixed-point `Decimal` arithmetic to guarantee financial precision down to single paise.
> 
> Looking at our project structure:
> 1. In `models/`, we enforce strict validation on Advertisers, Publishers, and Campaigns, distinguishing prepaid wallets from credit limits.
> 2. In `services/`, domain responsibilities are decoupled:
>    - `eligibility.py` handles multi-dimensional targeting and flight dates.
>    - `frequency_service.py` tracks user impressions across calendar days and clock hours in IST.
>    - `budget_service.py` tracks hourly pacing against diurnal traffic profiles and activates parity throttling.
>    - `auction.py` implements the Vickrey second-price auction mechanism.
>    - `billing_service.py` manages wallet debits, credit suspensions, and publisher monthly rev-share.
>    - And `click_service.py` operates a rolling 10-minute sliding window to detect invalid traffic and trigger automatic clawbacks."

---

### [1:45 - 3:00] Live Simulation Run & Output Verification
**Visual**: Open terminal in project root and run `python main.py data/commands.txt`.

**Yashwanth S**:
> "Let's demonstrate the engine live. We execute `python main.py data/commands.txt`.
> 
> *(Run command in terminal)*
> 
> As you can see, the engine:
> 1. Ingests all advertiser accounts, publisher floors, campaign parameters, and historical CTRs.
> 2. Merges ad requests and click streams chronologically into a single priority queue.
> 3. Executes the simulation day by day—opening October 12th, processing all hourly events up to 23:59:59, closing the day, and repeating through October 14th.
> 
> Over 1,400 ad requests were processed with complete determinism.
> 
> The run outputs all four evaluation CSV deliverables:
> - `auction_log.csv`: Every request outcome, candidate eCPMs, winner, and clearing CPM.
> - `click_log.csv`: Status of all clicks, billed CPC amounts, and invalidation flags.
> - `daily_campaign_report.csv`: Daily impressions, clicks, spend, and pacing status.
> - `publisher_payout.csv`: Month-to-date billed amounts, 60% vs 70% revenue share tiers, clawbacks, and rollover balances."

---

### [3:00 - 4:00] Planted Edge Cases Verification (EC-01 to EC-08)
**Visual**: Open `output/auction_log.csv` and `output/click_log.csv` highlighting specific lines.

**Yashaswini**:
> "Our engine successfully detects and verifies all 8 planted edge cases:
> - **EC-01**: In `REQ-000466`, only `CMP-001` bids above `PUB-5`'s floor of Rs 150. As a single bidder, it clears at exactly the floor price of Rs 150.00 CPM without any increment.
> - **EC-02**: In `REQ-000171`, `CMP-004` bids 180 and `CMP-005` bids 90 below the floor of 120. The winner clears at $\max(90.00, 120.00) + 0.01 = \text{Rs } 120.01$.
> - **EC-03**: In `REQ-000087`, `CMP-006` reaches exactly 1,000 trailing impressions in history, switching from the default 0.5% CTR to its actual 0.7% CTR.
> - **EC-04**: At hour 0, `CMP-001` exceeds 120% pacing schedule and enters `OVER_PACE`. It is throttled and sits out on odd request `REQ-000519`.
> - **EC-05**: User `U77770001` reaches their daily cap of 3 impressions at 23:59:00; request at 23:59:30 is capped, but at 00:00:00 next day, cap resets and the ad serves.
> - **EC-06**: Six clicks on `CMP-006` arrive within 10 minutes. All six clicks are marked `INVALID`, CPC charges refunded, and Rs 90 clawed back from `PUB-4`.
> - **EC-07**: `PUB-5` reaches exactly Rs 1,00,000.00 MTD. Because the rule requires strictly greater than 1,00,000 for 70%, it correctly remains in the 60% tier.
> - **EC-08**: In `REQ-001079`, `ADV-07` breaches its credit limit by 1 paisa (balance hits -50,000.01). The charge stands and the account is immediately suspended."

---

### [4:00 - 4:45] Automated Unit Test Suite
**Visual**: Switch terminal and run `python -m pytest tests -v`.

**Yashwanth S**:
> "Quality assurance was driven by test-first engineering. Let's run our test suite using `python -m pytest tests -v`.
> 
> *(Run pytest in terminal)*
> 
> All **50 unit and integration tests** pass in under 0.5 seconds.
> - `test_br01_to_br12.py` tests every individual business rule.
> - `test_edge_cases.py` provides targeted verification for all 8 planted scenarios.
> - `test_frequency.py` tests boundary conditions across clock hours and midnight IST.
> - `test_models_and_services.py` verifies data model integrity and end-to-end integration."

---

### [4:45 - 5:00] Conclusion & Wrap-Up
**Visual**: Show `docs/DESIGN_DOCUMENT.html` or GitHub repo landing page.

**Yashaswini & Yashwanth**:
> "In conclusion, our engine fulfills 100% of the functional, mathematical, and reporting specifications for PS-091 with zero defect escape.
> 
> Both of us are fully prepared for our Week 4 final evaluation and 15-minute viva, including the live code modification challenge.
> 
> Thank you!"
