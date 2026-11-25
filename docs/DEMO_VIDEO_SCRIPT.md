# 5-Minute Demo Video Script & Walkthrough Guide
## PS-091: Digital Ad Auction, Budget Pacing and Frequency-Cap Engine
**Team ID**: T049 | **Domain**: Media - AdTech  
**Team Members**: Yashwanth S ([@yashwanth06s](https://github.com/yashwanth06s)) & Yashaswini ([@yashaswini3135](https://github.com/yashaswini3135))  
**Placement Coaching Capstone Project** — 10 SECONDS

---

## Video Specifications & Metadata (Recorded Video: `VED PROJ.mp4`)
- **Actual Duration**: **4 minutes 34 seconds** (273.87 seconds — strictly within the 5-minute cap).
- **Resolution**: 1080p Full HD (1920 × 1080), 30 fps.
- **Audio Track**: AAC Stereo voiceover narration by Yashaswini.
- **Visual Presentation**: Screen walkthrough conducted in VS Code / Antigravity by Yashwanth S.

---

## Minute-by-Minute Presentation Timeline

| Time Window | Visual on Screen | Narration Focus |
|---|---|---|
| **0:00 – 0:40** | VS Code / GitHub showing `README.md` with Team T049, PS-091, team members, and project overview | Introduction, Problem Statement, and Domain Significance |
| **0:40 – 1:30** | Expanding `models/`, `services/`, and reviewing `auction.py`, `budget_service.py`, `click_service.py` | System Architecture, Decimal Precision, and Modular Services |
| **1:30 – 2:45** | Terminal executing `python main.py data/commands.txt`, scrolling through daily reports | Live Event Queue Ingestion, Simulation Run, and Daily Reports |
| **2:45 – 3:45** | Opening `output/auction_log.csv`, `output/click_log.csv`, and `output/publisher_payout.csv` | Output Deliverables & Planted Edge Cases (EC-01, EC-02, EC-04, EC-06, EC-07) |
| **3:45 – 4:15** | Terminal executing `python -m pytest tests -v` with all 50 tests passing green | Quality Assurance, Test Suite Coverage (BR-01..BR-12, EC-01..EC-08) |
| **4:15 – 4:34** | Wrapping up on `README.md` / `DESIGN_DOCUMENT.html` | Conclusion, Submission Readiness, and Viva Preparation |

---

## Word-for-Word Voiceover Script

### [0:00 – 0:40] Introduction & Problem Overview
*(Visual on screen: VS Code showing `README.md` with Team T049, PS-091, and both names)*

> "Hello everyone. Welcome to our Capstone Project presentation for **PS-091: Digital Ad Auction, Budget Pacing, and Frequency-Cap Engine**.
> 
> We are **Team T049**, representing the Media and AdTech domain. My name is **Yashaswini**, and my teammate is **Yashwanth S**.
> 
> In digital programmatic advertising, ad exchanges process thousands of ad requests and click events every second. Our challenge was to design and implement a high-precision, deterministic decision engine in Python that executes Vickrey second-price auctions with publisher reserve floors, controls advertiser budget pacing across twenty-four hourly buckets, enforces strict per-user frequency caps, detects Invalid Traffic using sliding time windows, and settles monthly publisher payouts with revenue sharing and clawbacks."

---

### [0:40 – 1:30] System Architecture & Modular Design
*(Visual on screen: Expanding `models/`, `services/`, and clicking on `services/auction.py`, `budget_service.py`, `click_service.py`)*

> "Looking at our project structure, we designed the engine following strict object-oriented and modular principles with zero external runtime dependencies. We use Python’s fixed-point `Decimal` arithmetic to guarantee financial accuracy down to individual paise.
> 
> - In the **`models/`** directory, we maintain strongly validated dataclasses for Advertisers, Campaigns, and Publishers, separating prepaid wallets from credit facilities.
> - In the **`services/`** layer, each domain responsibility is cleanly decoupled:
>   - `eligibility.py` validates multi-dimensional targeting and flight date boundaries.
>   - `frequency_service.py` tracks user impressions across calendar days and clock hours in IST.
>   - `budget_service.py` calculates hourly budget buckets based on the empirical traffic profile and applies parity throttling when campaigns over-pace.
>   - `auction.py` executes the second-price clearing mechanics with publisher reserve floors.
>   - `click_service.py` operates a rolling ten-minute sliding window to catch invalid traffic.
>   - And `billing_service.py` manages wallet debits, credit suspensions, and tiered publisher payouts."

---

### [1:30 – 2:45] Live Simulation Execution & Console Output
*(Visual on screen: In the terminal, executing `python main.py data/commands.txt`, scrolling through daily reports)*

> "Now, let’s run the engine live against the sample command stream. In the terminal, we execute:
> `python main.py data/commands.txt`.
> 
> As you can see, the engine:
> 1. Ingests all advertisers, campaigns, publisher floors, and 7-day historical CTR data.
> 2. Merges ad requests and click interactions chronologically into a single priority queue.
> 3. Executes the simulation day by day: opening October 12th, processing all hourly events up to 23:59:59, closing the day, and repeating seamlessly through October 14th.
> 
> In total, over fourteen hundred ad requests were processed with complete determinism. The terminal prints daily campaign performance summaries—displaying served impressions, clicks, daily spend, and pacing status—concluding with the October publisher revenue settlement."

---

### [2:45 – 3:45] Output CSV Deliverables & Planted Edge Cases
*(Visual on screen: Opening `output/auction_log.csv`, `output/click_log.csv`, and `output/publisher_payout.csv`)*

> "The engine automatically exports all four required evaluation deliverables into the `output/` directory:
> 
> 1. **`auction_log.csv`**: Records every request outcome. Here, our engine verifies:
>    - **EC-01**: In `REQ-000466`, `CMP-001` is the single bidder meeting `PUB-5`'s floor of 150. As a single bidder, it clears at exactly the floor price of 150 CPM without any increment.
>    - **EC-02**: In `REQ-000171`, the second bid is below the floor, so the winner clears at floor plus one paisa, which is 120.01 CPM.
>    - **EC-04**: At hour 0, `CMP-001` reaches 120% pacing, enters `OVER_PACE`, and sits out on odd request `REQ-000519`.
> 2. **`click_log.csv`**: Shows click billing and fraud detection. 
>    - Under **EC-06**, clicks `CLK-00057` to `62` arrive within 10 minutes. The engine flags all six clicks as `INVALID`, reverses the CPC charges, and registers a ninety-rupee clawback against `PUB-4`.
> 3. **`publisher_payout.csv`**:
>    - Under **EC-07**, `PUB-5` reaches exactly one lakh rupees MTD. Because the rule requires strictly greater than one lakh for 70%, it correctly remains in the 60% revenue share tier."

---

### [3:45 – 4:15] Automated Test Suite Execution
*(Visual on screen: In the terminal, typing `python -m pytest tests -v` and printing all 50 passing tests)*

> "Quality assurance was built test-first. Let's run our test suite using `python -m pytest tests -v`.
> 
> All **fifty automated unit and integration tests** pass in under one second. 
> - `test_br01_to_br12.py` tests every individual business rule.
> - `test_edge_cases.py` provides targeted verification for all eight planted scenarios.
> - `test_frequency.py` validates boundary conditions across clock hours and midnight IST.
> - And `test_models_and_services.py` verifies data model integrity and end-to-end pipeline execution."

---

### [4:15 – 4:34] Conclusion & Viva Readiness
*(Visual on screen: Showing `README.md` or `docs/DESIGN_DOCUMENT.html`)*

> "In conclusion, our engine successfully implements all twelve business rules, verifies all eight planted edge cases, and generates all required evaluation reports with complete accuracy. 
> 
> Both Yashwanth and I have reviewed our decision log and architecture, and we are fully prepared for our Week 4 evaluation and viva, including the live code modification challenge.
> 
> Thank you!"
