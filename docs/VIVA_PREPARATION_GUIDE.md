# Comprehensive Viva Preparation & Live Code Change Guide
## PS-091: Digital Ad Auction, Budget Pacing and Frequency-Cap Engine
**Team ID**: T049 | **Domain**: Media - AdTech | **Tech Stack**: Python 3.12+  
**Team Members**: Yashwanth S ([@yashwanth06s](https://github.com/yashwanth06s)) & Yashaswini ([@yashaswini3135](https://github.com/yashaswini3135))  
**Placement Coaching Capstone Project** — 10 SECONDS (Week 4 Final Submission)

---

## 1. Viva Format & Examination Rules
- **Duration**: **15 minutes per student** (30 minutes total for Team T049).
- **Mandatory Requirements**:
  - Minimum score to pass: **50 / 100**.
  - Code similarity above 40% = **Immediate Fail**.
  - Inability to perform a live code modification in the viva = **Immediate Fail**.
- **Viva Structure Breakdown**:
  1. **Minutes 0 – 3**: High-level individual contribution & architecture walkthrough.
  2. **Minutes 3 – 8**: Theoretical and domain questioning (AdTech mechanics, edge cases, formulas).
  3. **Minutes 8 – 13**: **Live Code Change Challenge** (screen shared, modify logic, run tests to verify).
  4. **Minutes 13 – 15**: Evaluation of modified code, git diff inspection, and scoring.

---

## 2. Core Domain Knowledge Q&A

### Q1: What is eCPM, and why must CPC bids be normalized into eCPM?
**Answer**:
- **CPM** (Cost Per Mille) bids represent price per 1,000 impressions.
- **CPC** (Cost Per Click) bids represent price paid only when a user clicks.
- In a unified auction, the publisher sells *impressions*. To compare a CPC bid against a CPM bid fairly, the engine calculates the **Effective CPM (eCPM)**:
  $$\text{eCPM} = \text{CPC Bid} \times \text{CTR} \times 1,000$$
- This estimates expected revenue per 1,000 impressions. If a CPC campaign bids Rs 25.00 with a CTR of 0.7% (0.007), its eCPM is $25.00 \times 0.007 \times 1000 = \text{Rs } 175.00$.

### Q2: How does a Second-Price (Vickrey) Auction clear when reserve floor prices are introduced?
**Answer**:
- In standard Vickrey auctions without floors, the winner pays the second-highest bid plus the minimum bid increment (Rs 0.01).
- With a publisher floor:
  1. Any candidate with $\text{eCPM} < \text{Floor}$ cannot win.
  2. **Single bidder above floor (EC-01)**: Pays exactly the floor price (no increment).
  3. **Multiple bidders (EC-02)**: The winner pays:
     $$\text{Clearing CPM} = \max(\text{second-highest eCPM}, \text{publisher floor}) + \text{Rs } 0.01$$
  4. Example (EC-02): Bidder 1 bids 180, Bidder 2 bids 90, Floor is 120. $\max(90, 120) + 0.01 = \text{Rs } 120.01\text{ CPM}$.

### Q3: What is Budget Pacing, and why did you choose Parity Throttling over random dropping?
**Answer**:
- Ad traffic is not uniform; it follows a diurnal curve (low at 3 AM, high at 9 PM). Budget pacing spreads a daily budget across 24 hourly buckets matching the traffic profile.
- **Threshold**: When spend reaches $\ge 120\%$ of cumulative scheduled budget, the campaign is marked `OVER_PACE`.
- **Why Parity Throttling?**: Random probabilistic dropping ($50\%$ random drop) is non-deterministic, making logs irreproducible. Parity throttling filters on $\text{request\_seq\_no} \pmod 2 == 0$, providing guaranteed reproducible execution and auditable evaluation logs.

### Q4: How does your Invalid Traffic (IVT) sliding window work?
**Answer**:
- Fraudulent click bursts occur rapidly. We maintain a deque/list of click timestamps per $(user\_id, campaign\_id)$.
- When a click arrives, we check if there are $> 5$ clicks (i.e. $\ge 6$ clicks) within a 10-minute window (600 seconds).
- If triggered:
  1. All clicks within the burst window are marked `INVALID`.
  2. The advertiser's wallet or credit line is refunded.
  3. The publisher revenue share credited for those clicks is clawed back from their monthly payout.

### Q5: Why did you use `decimal.Decimal` instead of Python `float`?
**Answer**:
- IEEE 754 floating-point arithmetic suffers from binary rounding errors (e.g., $0.1 + 0.2 = 0.30000000000000004$).
- Financial ad billing deals with single paise and micro-transactions (Rs 0.15/impression, 1 paisa increments).
- `Decimal` provides exact fixed-point precision, ensuring credit limit breaches by exactly Rs 0.01 (EC-08) and exact Rs 1,00,000 revenue tiers (EC-07) are evaluated without floating-point drift.

---

## 3. Student-Specific Viva Questioning

### For Yashwanth S (Auction, Pacing, Billing & Data Modeling)
- **Role**: Second-Price Auction, Budget Pacing, Billing Mechanics, System Architecture.
- **Likely Questions**:
  1. *Walk me through the tie-breaking logic in `services/auction.py`.*  
     **Answer**: In BR-05, candidates are sorted primarily by eCPM descending. Equal eCPMs are resolved first by lower cumulative spend today (giving under-spent campaigns a boost), and second by ascending alphanumeric `campaign_id`.
  2. *What happens when a credit advertiser exceeds their credit limit during an auction? (EC-08)*  
     **Answer**: The winning impression charge is permitted to complete (the charge stands), pushing the account into breach (e.g. balance of -50,000.01 on a 50,000 limit). The advertiser is immediately marked `suspended = True`, and all subsequent requests for this advertiser remain unfilled.
  3. *How does catch-up spending work in UNDER_PACE mode?*  
     **Answer**: Under-pacing campaigns are allowed to spend up to 150% of the current hour's allocated bucket in that hour to catch up with schedule delivery.

### For Yashaswini (Frequency Capping, IVT Detection, Publisher Payouts & Tests)
- **Role**: User Frequency Capping, IVT Detection & Clawbacks, Publisher Settlements, Test Automation.
- **Likely Questions**:
  1. *How are frequency caps tracked without querying an external database?*  
     **Answer**: In `services/frequency_service.py`, we use composite in-memory dictionary keys: `(campaign_id, user_id, str(request_date))` for the daily cap (max 3), and `(campaign_id, user_id, str(request_date), int(hour))` for the clock-hour cap (max 1). Lookups and updates are $O(1)$.
  2. *How is publisher rollover calculated in `services/billing_service.py`?*  
     **Answer**: Net Payout $= \text{Share Amount} + \text{Rollover In} - \text{Clawback}$. If this amount is $< \text{Rs } 5,000$, `payout_due` is set to $0.00$, and the full net amount is stored in `rolled_to_next` to be added into the subsequent month's settlement.
  3. *How do you test that trailing CTR defaults to 0.5% and switches at 1000 impressions? (EC-03)*  
     **Answer**: In `tests/test_edge_cases.py::test_ec03_cpc_exactly_1000_impressions`, we assert that 999 impressions yields a CTR of `0.005`, while 1000 impressions with 7 valid clicks switches immediately to `0.007`.

---

## 4. Live Code Change Simulation (8 Anticipated Challenges)

Examiners are required to test your understanding by asking you to make one live code change during the viva. Below are the 8 most likely challenges with exact code diffs and verification commands.

---

### Challenge 1: Modify Frequency Cap Limits (e.g., 5 per day, 2 per hour)
- **Examiner Request**: *"Change the default frequency cap from 3/day and 1/hour to 5/day and 2/hour."*
- **File to Edit**: `models/campaign.py` (or `services/frequency_service.py`)
- **Code Change**:
```python
# In models/campaign.py
# Default parameters or instantiation:
freq_cap_day: int = 5    # was 3
freq_cap_hour: int = 2   # was 1
```
- **Verification Command**:
```bash
python -m pytest tests/test_frequency.py -v
```

---

### Challenge 2: Change Parity Throttling from 50% to 1-in-3 Throttling
- **Examiner Request**: *"Instead of bidding on even requests (`seq_no % 2 == 0`), modify throttling so an over-paced campaign bids only on every 3rd request (`seq_no % 3 == 0`)."*
- **File to Edit**: `services/budget_service.py`
- **Location**: Line ~55 in `can_bid()`
- **Diff**:
```diff
  if status == "OVER_PACE":
-     if int(request_sequence) % 2 != 0:
+     if int(request_sequence) % 3 != 0:
          return False, status, "Throttled: over pace on odd request sequence"
      return True, status, ""
```
- **Verification Command**:
```bash
python main.py data/commands.txt
```

---

### Challenge 3: Modify Invalid Traffic (IVT) Burst Threshold
- **Examiner Request**: *"Change IVT detection from >5 clicks in 10 minutes to >3 clicks in 5 minutes."*
- **File to Edit**: `services/click_service.py`
- **Location**: Lines ~57-61 in `process_click()`
- **Diff**:
```diff
- if n >= 6:
+ if n >= 4:
      for i in range(n):
-         for j in range(i + 5, n):
-             if history[j]["click_ts"] - history[i]["click_ts"] <= timedelta(minutes=10):
+         for j in range(i + 3, n):
+             if history[j]["click_ts"] - history[i]["click_ts"] <= timedelta(minutes=5):
```
- **Verification Command**:
```bash
python -m pytest tests/test_br01_to_br12.py -k "ivt" -v
```

---

### Challenge 4: Add a 3-Tier Publisher Revenue Share Structure
- **Examiner Request**: *"Modify publisher revenue sharing: if monthly billed <= 50,000, 50% share; if 50,000 to 1,50,000, 65% share; if > 1,50,000, 75% share."*
- **File to Edit**: `services/billing_service.py`
- **Location**: Lines ~113 & ~128 in `reverse_click()` and `get_publisher_payout()`
- **Diff**:
```diff
- share_pct = 70 if mtd_billed > Decimal("100000.00") else 60
+ if mtd_billed > Decimal("150000.00"):
+     share_pct = 75
+ elif mtd_billed > Decimal("50000.00"):
+     share_pct = 65
+ else:
+     share_pct = 50
```
- **Verification Command**:
```bash
python main.py data/commands.txt
```

---

### Challenge 5: Modify Second-Price Auction Increment from Rs 0.01 to Rs 0.05
- **Examiner Request**: *"Change the second-price clearing increment from 1 paisa (Rs 0.01) to 5 paise (Rs 0.05)."*
- **File to Edit**: `services/auction.py`
- **Location**: Line ~74 in `run_second_price_auction()`
- **Diff**:
```diff
- clearing_cpm = max(second_ecpm, floor) + Decimal("0.01")
+ clearing_cpm = max(second_ecpm, floor) + Decimal("0.05")
```
- **Verification Command**:
```bash
python -m pytest tests/test_edge_cases.py -k "ec02" -v
```

---

### Challenge 6: Modify Auction Tie-Breaker to Favor Higher Remaining Daily Budget
- **Examiner Request**: *"If two campaigns tie on eCPM, break the tie by higher remaining daily budget instead of lower cumulative spend."*
- **File to Edit**: `services/auction.py`
- **Location**: Lines ~38-45 in `run_second_price_auction()`
- **Diff**:
```diff
  sorted_candidates = sorted(
      candidates,
      key=lambda c: (
          -Decimal(str(c["ecpm"])),
-         Decimal(str(c["spend_today"])),
+         -(Decimal(str(c["campaign"].daily_budget)) - Decimal(str(c["spend_today"]))),
          str(c["campaign_id"])
      )
  )
```
- **Verification Command**:
```bash
python -m pytest tests/test_br01_to_br12.py -k "tie" -v
```

---

### Challenge 7: Change Publisher Payout Rollover Threshold to Rs 2,500
- **Examiner Request**: *"Reduce the publisher payout rollover threshold from Rs 5,000 to Rs 2,500."*
- **File to Edit**: `services/billing_service.py`
- **Location**: Line ~137 in `get_publisher_payout()`
- **Diff**:
```diff
- if total_due < Decimal("5000.00"):
+ if total_due < Decimal("2500.00"):
      actual_payout = Decimal("0.00")
      rolled_to_next = total_due
```
- **Verification Command**:
```bash
python -m pytest tests/test_br01_to_br12.py -k "rollover" -v
```

---

### Challenge 8: Change Cold-Start Trailing Impressions Threshold from 1,000 to 500
- **Examiner Request**: *"Switch from default CTR of 0.5% to actual CTR at 500 impressions instead of 1,000."*
- **File to Edit**: `services/bidding.py`
- **Location**: Line ~15 in `calculate_ctr()`
- **Diff**:
```diff
- if impressions < 1000:
+ if impressions < 500:
      return Decimal("0.005")
```
- **Verification Command**:
```bash
python -m pytest tests/test_edge_cases.py -k "ec03" -v
```

---

## 5. Quick Troubleshooting Commands During Viva

If asked to run specific checks live:
1. **Run full 50-test suite with verbose test names**:
   ```bash
   python -m pytest tests -v
   ```
2. **Run only edge cases**:
   ```bash
   python -m pytest tests/test_edge_cases.py -v
   ```
3. **Execute engine simulation on sample data**:
   ```bash
   python main.py data/commands.txt
   ```
4. **Inspect git status & recent commits**:
   ```bash
   git status
   git log -n 5 --oneline
   ```
