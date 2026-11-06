# PS-091 – Digital Ad Auction, Budget Pacing and Frequency-Cap Engine — Sample Data Pack

Prepared by 10 SECONDS for Team T049.

## Files

| File | What it holds | Row count |
|---|---|---|
| `traffic_profile.csv` | Share of the daily budget scheduled for each IST hour (sums to 100) | 24 data rows |
| `advertisers.csv` | 8 advertisers: prepaid wallet or credit account | 8 data rows |
| `publishers.csv` | 5 publishers: floor CPM, month-to-date billed before 2026-10-12, payout rolled over | 5 data rows |
| `campaigns.csv` | 20 campaigns: flight, daily budget, CPM/CPC bid, targeting, frequency caps | 20 data rows |
| `campaign_history.csv` | Daily impressions / valid clicks of CPC campaigns for the 7 days before the file (trailing CTR) | 21 data rows |
| `ad_requests.csv` | Ad requests 2026-10-12 .. 2026-10-14 in time order | 1417 data rows |
| `clicks.csv` | Clicks on served impressions | 119 data rows |
| `commands.txt` | Day open / processing / close and print requests | 14 command lines (excluding comments) |

Volumes in this sample are reduced for email delivery; the hidden evaluation set is larger and uses the same schema.

Row numbers quoted below are 1-based data-row numbers (the header is row 0). Line numbers for `commands.txt` are physical line numbers including comment lines.

## Column reference

Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals with 2 places (no commas, no symbol); percentages as plain numbers (12.5 means 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix. An empty cell means "not applicable" and only occurs in columns whose notes say so.

### `traffic_profile.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| hour | int | IST hour | 0-23 | — |
| pct_of_daily_budget | decimal | % | — | bucket = daily_budget x pct / 100 |

### `advertisers.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| advertiser_id | string | ADV-nn | — | — |
| advertiser_name | string | — | — | — |
| account_type | enum | — | PREPAID, CREDIT | — |
| wallet_balance | decimal | Rs | — | opening balance; negative allowed for CREDIT |
| credit_limit | decimal | Rs | — | CREDIT: balance may go down to -credit_limit |

### `publishers.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| publisher_id | string | PUB-n | — | — |
| publisher_name | string | — | — | — |
| floor_cpm | decimal | Rs per 1,000 | — | — |
| mtd_billed_before | decimal | Rs | — | October billing before 2026-10-12 |
| rollover_payout | decimal | Rs | — | payout carried from September (< Rs 5,000) |

### `campaigns.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| campaign_id | string | CMP-nnn | — | — |
| advertiser_id | string | — | advertisers.csv | — |
| flight_start | date | — | — | — |
| flight_end | date | — | — | serves until 23:59:59 |
| daily_budget | decimal | Rs | — | — |
| bid_type | enum | — | CPM, CPC | — |
| max_bid | decimal | Rs | — | CPM: per 1,000 impressions; CPC: per click |
| target_geos | string | ';'-separated | KA, MH, DL, TN, TS, WB, GJ, KL | — |
| target_devices | string | ';'-separated | MOBILE, DESKTOP, TABLET | — |
| target_categories | string | ';'-separated | — | all three dimensions must match |
| freq_cap_day | int | — | 3 | per user per IST day |
| freq_cap_hour | int | — | 1 | per user per IST clock hour |

### `campaign_history.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| campaign_id | string | — | campaigns.csv | CPC campaigns only |
| date | date | — | — | — |
| impressions | int | — | — | — |
| valid_clicks | int | — | — | — |

### `ad_requests.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| request_id | string | REQ-nnnnnn | — | sequence number = numeric part |
| request_ts | timestamp | IST | — | sorted |
| publisher_id | string | — | publishers.csv | — |
| user_id | string | — | — | — |
| geo | string | — | — | — |
| device | enum | — | MOBILE, DESKTOP, TABLET | — |
| category | string | — | — | — |

### `clicks.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| click_id | string | CLK-nnnnn | — | — |
| request_id | string | — | ad_requests.csv | the impression clicked |
| user_id | string | — | — | — |
| click_ts | timestamp | IST | — | — |

## Command file format

`commands.txt` holds one command per line in the form `COMMAND_NAME|arg1|arg2|...`. Commands must be processed strictly in file order. Lines starting with `#` are comments and blank lines are ignored. An empty argument (two pipes in a row) means "not supplied". Every command used in this pack:

| Command | Arguments (in order) | Meaning |
|---|---|---|
| `OPEN_DAY` | `YYYY-MM-DD` | Reset daily spend, frequency caps and pacing; recompute trailing 7-day CTR for CPC campaigns |
| `PROCESS_UNTIL` | `timestamp` | Process requests and clicks up to the instant |
| `CLOSE_DAY` | `YYYY-MM-DD` | Close the day (unspent budget lapses) |
| `PRINT_DAILY_REPORT` | `YYYY-MM-DD` | Campaign report: spend, impressions, clicks, pacing status |
| `PRINT_PUBLISHER_PAYOUT` | `YYYY-MM` | Publisher payout for the month so far |
| `PRINT_AUCTION_LOG` | `from_date|to_date` | Per-request auction outcome |

## Planted scenarios

Every edge case in the brief, mapped to the exact record where it occurs, followed by extra traps.

- **EC-01 Single bidder whose bid equals the floor exactly**
  - REQ-000466 on PUB-5 (floor Rs 150.00 CPM): the only eligible campaign CMP-001 bids CPM 150.00 = the floor exactly -> it meets the floor and, as a single bidder, pays the floor (Rs 0.15 per impression) — `ad_requests.csv REQ-000466 (row 466); campaigns.csv CMP-001 (row 1)`
- **EC-02 Second-highest bid below floor - winner pays floor plus increment**
  - REQ-000171 on PUB-4 (floor 120.00): bids CMP-004 180.00 and CMP-005 90.00 (below the floor) -> winner pays max(90.00, 120.00) + 0.01 = 120.01 CPM — `ad_requests.csv REQ-000171 (row 171); campaigns.csv CMP-004 (row 4); campaigns.csv CMP-005 (row 5)`
- **EC-03 CPC campaign with exactly 1,000 trailing impressions switching from default CTR**
  - CMP-006 (CPC Rs 25.00): campaign_history.csv has exactly 1,000 impressions and 7 valid clicks in the 7 days before 2026-10-12 -> not 'fewer than 1,000' -> uses its own CTR 0.7% (not the 0.5% default): eCPM = 25 x 0.007 x 1000 = 175.00, first won request REQ-000087 — `campaigns.csv CMP-006 (row 6); ad_requests.csv REQ-000087 (row 87); campaign_history.csv rows 1-7`
- **EC-04 Campaign at 120.0 percent of scheduled budget at the hour boundary**
  - CMP-001 (daily budget 400, hour-0 profile 1.5% -> scheduled Rs 6.00): the 48 single-bidder wins between 00:00 and 00:58 on 2026-10-13 cost 48 x 0.15 = Rs 7.20 = exactly 120.0% -> OVER_PACE; request REQ-000519 at 00:59:59 has an odd sequence number -> the campaign sits out -> UNFILLED; at the hour boundary REQ-000520 (01:00:00) the schedule includes hour 1 -> back under 120% -> it bids and wins — `campaigns.csv CMP-001 (row 1); ad_requests.csv REQ-000519 (row 519); ad_requests.csv REQ-000520 (row 520); ad_requests.csv rows 466-517 (the 48 hour-0 requests)`
- **EC-05 Frequency cap: 3rd impression at 23:59 and request at 00:00 next day**
  - User U77770001 gets CMP-002's 3rd impression of 2026-10-12 at 23:59:00 (REQ-000463); the request at 23:59:30 (REQ-000464) is frequency-capped; the request at 00:00:00 on 2026-10-13 (REQ-000465) is a new IST day and a new clock hour -> eligible, served — `ad_requests.csv REQ-000463 (row 463); campaigns.csv CMP-002 (row 2); ad_requests.csv REQ-000464 (row 464); ad_requests.csv REQ-000465 (row 465); ad_requests.csv REQ-000103 (row 103); ad_requests.csv REQ-000274 (row 274)`
- **EC-06 6th click arriving exactly 10 minutes after the 1st**
  - Clicks CLK-00057 .. CLK-00062 by U66660042 on CMP-006 (all on impression REQ-000740): the 6th arrives exactly 10:00 after the 1st -> 6 clicks within 10 minutes (> 5) -> all six INVALID, their CPC billing reversed and PUB-4's share clawed back from the next payout — `clicks.csv CLK-00057 (row 57); clicks.csv CLK-00058 (row 58); clicks.csv CLK-00059 (row 59); clicks.csv CLK-00060 (row 60); clicks.csv CLK-00061 (row 61); clicks.csv CLK-00062 (row 62)`
- **EC-07 Publisher at exactly Rs 1,00,000 billed in the month**
  - PUB-5: mtd_billed_before 99982.60 + Rs 17.40 billed in this file = exactly Rs 1,00,000.00 for October -> not above 1,00,000 -> 60% revenue share — `publishers.csv PUB-5 (row 5)`
- **EC-08 Credit advertiser whose winning bid would exceed credit limit by Rs 0.01**
  - ADV-07 (credit limit 50,000.00, opening balance -49995.51): the win REQ-001079 costs Rs 0.15 and takes the balance to -50,000.01 = Rs 0.01 beyond the limit -> the charge stands and the advertiser is SUSPENDED; its campaign CMP-003 does not bid again (12 later SPIRITUAL requests on PUB-5 stay UNFILLED) — `advertisers.csv ADV-07 (row 7); ad_requests.csv REQ-001079 (row 1079)`
- **Extra traps (not in the brief, but realistic):**
  - CMP-012 ends its flight on 2026-10-13 (serves until 23:59:59) and CMP-014 starts on 2026-10-13 — neither bids on days outside its flight; unspent budget is not carried forward — `campaigns.csv CMP-012 (row 12); campaigns.csv CMP-014 (row 14)`
  - REQ-001025: CMP-007 and CMP-008 both bid 130.00 CPM on PETCARE (PUB-3, floor 90.00) with equal spend today -> tie goes to the lower campaign_id; clearing 130.00 + 0.01 = 130.01. In REQ-001028 the earlier winner now has the higher spend today -> the other campaign wins — `ad_requests.csv REQ-001025 (row 1025); ad_requests.csv REQ-001028 (row 1028); campaigns.csv CMP-007 (row 7); campaigns.csv CMP-008 (row 8)`
  - REQ-000288: REAL_ESTATE request on MOBILE -> only CMP-005 (90.00) is eligible and it is below the PUB-4 floor 120.00 -> UNFILLED (no bid meets the floor) — `ad_requests.csv REQ-000288 (row 288)`

## What is NOT in this pack

Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation

Produce these CSV files (header row, same conventions as above, rows sorted as stated). Where the brief is silent on a format detail the choice below is binding for evaluation.

### `auction_log.csv`

One row per request.

Columns, in order: `request_id`, `outcome`, `winner_campaign_id`, `winner_ecpm`, `second_ecpm`, `clearing_cpm`, `bidders`, `reason`

### `click_log.csv`

One row per click.

Columns, in order: `click_id`, `request_id`, `campaign_id`, `status`, `billed_amount`, `reversed`

### `daily_campaign_report.csv`

One row per campaign per day.

Columns, in order: `date`, `campaign_id`, `impressions`, `valid_clicks`, `invalid_clicks`, `spend`, `budget`, `pacing_status_end`, `unfilled_due_to_throttle`

### `publisher_payout.csv`

One row per publisher for October.

Columns, in order: `publisher_id`, `mtd_billed`, `share_pct`, `share_amount`, `clawback`, `rollover_in`, `payout_due`, `rolled_to_next`

Binding choices where the brief is silent: pacing state is evaluated before each request with spend_today and the cumulative schedule through the current hour: OVER_PACE if spend >= 120% (then only even request sequence numbers), UNDER_PACE if spend < 100% (no throttle, but at most 150% of the current hour's bucket may be spent in that hour), else ON_PACE. Eligibility also needs spend_today < daily_budget, a prepaid wallet >= one max bid (CPM bid / 1000 or CPC bid), a non-suspended credit account, and both frequency caps (IST day, IST clock hour). eCPM of CPC = bid x trailing CTR x 1000 (CTR from the previous 7 calendar days incl. campaign_history.csv; < 1,000 impressions -> 0.5%). Clearing CPM: single bidder pays the floor; otherwise max(second eCPM, floor) + 0.01. CPM charge per impression = clearing CPM / 1000 (kept exact, reports rounded to paise). A CPC click is billed at the bid if spend_today < daily_budget when it arrives. Credit accounts: a charge that takes the balance below -credit_limit stands and suspends the advertiser. IVT window: 6 or more clicks of a user on a campaign with last - first <= 10:00. Share 70% only when month billing > 1,00,000.
