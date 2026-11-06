# Architecture & Design Decision Log
## Project: Digital Ad Auction Engine (PS-091) — Team T049

| Decision ID | Area | Context & Alternatives Considered | Decision Taken | Rationale |
|---|---|---|---|---|
| **DEC-01** | Language Choice | Java 17+ vs. Python 3.10+ | Chosen **Python 3.13** | Rapid iteration, concise standard libraries for time-window calculations (`datetime`, `collections`), and quick live code modifications during viva. |
| **DEC-02** | Arithmetic Precision | Standard `float` vs. `decimal.Decimal` | Chosen **`decimal.Decimal`** | Prevents binary floating-point roundoff issues in financial calculations (paise rounding, credit limit checks, second-price increments of 0.01). |
| **DEC-03** | Event Merging | Sequential file passes vs. Merged chronological priority queue | Chosen **Timestamp-ordered priority queue** | Merges `ad_requests.csv` and `clicks.csv` in strict time sequence, with clicks taking precedence on identical seconds. |
| **DEC-04** | Frequency Tracking | Database/Redis vs. In-memory Composite Dictionaries | Chosen **In-memory dictionary with `(campaign, user, date/hour)` keys** | Fast $O(1)$ lookups; avoids external service dependencies; calendar day and clock hour transitions reset naturally via key formulation. |
| **DEC-05** | Budget Pacing Evaluation | Continuous moving average vs. Hourly bucket percentage | Chosen **Discrete hourly buckets per `traffic_profile.csv`** | Matches exact 10 SECONDS specification; cumulative scheduled budget evaluated through current hour with 120% threshold. |
| **DEC-06** | Throttling Mechanism | Random probabilistic dropping vs. Deterministic parity filter | Chosen **Deterministic request sequence number parity (`seq_no % 2 == 0`)** | Enforces reproducible, deterministic auction logs across evaluation runs. |
| **DEC-07** | Auction Floor Logic | Filtering sub-floor bids before sorting vs. Sorting all eligible bids and clearing with floor | Chosen **Sorting all eligible bids and applying $\max(\text{2nd\_bid}, \text{floor}) + 0.01$** | Correctly handles EC-02 where the second-highest bidder is below floor, without improperly eliminating them as a bidder. |
| **DEC-08** | IVT Detection | Fixed batch buckets vs. Sliding window queue | Chosen **Sliding time window per `(user_id, campaign_id)`** | Catches rolling 10-minute bursts across arbitrary time boundaries ($> 5$ clicks in 600 seconds). |
| **DEC-09** | IVT Reversal Accounting | Mutating historical ledger vs. Dedicated refund and clawback tracking | Chosen **Dedicated refund to wallet and publisher clawback counter** | Accurately preserves gross MTD billing while cleanly adjusting net payouts and maintaining audit trails. |
| **DEC-10** | Credit Suspension | Rejecting breaching bid vs. Permitting winning charge and suspending account | Chosen **Permit the winning charge and suspend account** | Satisfies EC-08 requirement where a charge pushing balance to -50,000.01 stands and suspends the advertiser. |
