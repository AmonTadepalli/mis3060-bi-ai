# Wildcat Capital Data Cleaning Report
**To:** Portfolio Committee | **From:** Amon Tadepalli | **Re:** Quality of the 8-table warehouse extract

## Executive summary
The extract is usable for reporting after cleaning, with three caveats the committee should know about. Of 555,401 raw rows, 555,176 are kept; 225 rows (0.04%) were moved to quarantine files, not deleted. Every one of the 13 table relationships now joins at 100%. Before cleaning, only 33.98% of transactions could be joined to all their reference tables, mainly because security IDs were stored as `45.0` instead of `45`.

The caveats:
1. **Fee revenue must come from `fact_fees`, not transactions.** The two sources disagree in every one of the 28,746 client-months they share. Transactions show $263.7M of Advisory Fee debits against $204.7M billed (1.29x).
2. **28% of trades are dated on weekends** (40,630 of 143,218 Buys and Sells). Monthly totals are fine; day-level analysis is not. These are flagged.
3. **75 clients have no risk profile on file.** I did not fill them in. Suitability reports will show them as blank.

## What changed
| Issue | Table | Rows | Action | How it was verified |
|---|---|---:|---|---|
| Near-duplicate clients (last name off by one letter) | dim_client | 25 | quarantine | All 25 match a kept client on 12 fields; none appear in any fact table |
| State spelled out ("Pennsylvania") | dim_client | 78 | standardize | Per-state totals = code count + name count |
| security_id stored as `45.0` | fact_transactions | 197,175 | convert | Join to dim_security: 0% before, 100% after |
| Transactions for unknown clients | fact_transactions | 200 ($10,888,495.37) | quarantine | 200 distinct IDs, none in dim_client |
| Negative shares on Buys | fact_transactions | 835 | convert | amount = shares x price: 99.58% before, 100% after |
| Returns stored as text (`9.28%`) | fact_portfolio_snapshot | 300 | convert | Every value within 0.00005 of alpha + benchmark |
| Trade on a non-trading day | fact_transactions | 40,630 | flag | `non_trading_day_flag` |
| Activity after account stopped reporting | fact_transactions | 2,410 | flag | `after_last_snapshot_flag`; all inactive clients |
| AUM stuck at $1,000.00 | fact_portfolio_snapshot | 420 | flag | `aum_floor_flag`; 92 clients |

Thirteen more issues were reviewed and deliberately left as is (see `decision_log.md`). Every changed cell (198,388) is listed in `data/audit/value_changes.csv`.

**Scorecard, raw to clean** (from `data_quality_scorecard.csv`; all other tables were 100% on every measure in both stages):

| Table | Key uniqueness | Type validity | Rule pass | Referential match |
|---|---|---|---|---|
| dim_client | 99.01% to 100% | 100% to 100% | 96.91% to 100% | 100% to 100% |
| fact_portfolio_snapshot | 100% to 100% | 99.98% to 100% | 99.77% to 100% | 100% to 100% |
| fact_transactions | 100% to 100% | 91.73% to 100% | 99.72% to 100% | 33.98% to 100% |

Reconciliations now agree at 100%: transaction amount = shares x price, fee = AUM basis x bps / 12, fee AUM basis = snapshot AUM, and advisor on every fact = the client's advisor.

## Key judgment calls
**1. Negative-share Buys were a sign error, not a mislabeled Sell.** For all 835, the dollar amount is positive and equals |shares| x price to the cent, and no Sell or Dividend has negative shares. The size of the trade is proven, so I removed the sign. *Risk:* if some were actually Sells, their direction is still wrong. Nothing in the data can show that, so txn_type is kept as recorded.

**2. Blank risk profiles were not filled in.** All 75 sit on the Balanced benchmark, which makes "Balanced" a tempting fill. But that benchmark appears to be the default assigned when no profile exists, so using it would be circular and would put a suitability answer on file that the client never gave. *Risk:* risk-profile reports carry a blank bucket. That is the accurate picture.

**3. The Advisory Fee mismatch was documented, not "fixed".** `fact_fees` reconciles exactly to AUM x bps / 12 and to the snapshot AUM, so it is the trustworthy source. I can't tell which transaction rows are wrong, so nothing was changed. *Risk:* anyone summing transaction fees will overstate fee revenue by about $59M.

**4. Weekend trades were flagged, not moved.** Shifting them to Monday would invent a trade date. At 28% of trades, quarantining would gut the table. *Risk:* day-of-week analysis is unreliable for flagged rows.

## Limitations
- **Extreme returns remain.** 977 snapshots show |YTD return| above 100% (max 94.67, i.e. +9,467%), all in Retail accounts. They reconcile internally, so they stay. An IQR test flags 10,067 returns (7.8%); flagged means "far from typical", not "wrong". Use medians for performance comparisons.
- **AUM outliers are real.** IQR flags 13,261 snapshots (10.2%) above $6.9M; 98.9% belong to UHNW clients, a legitimate segment.
- **Holdings can't be rebuilt from transactions.** 42,975 Sells exceed the shares bought earlier, because the extract has no opening positions. Use snapshots for positions.
- **7,350 snapshot months have no fee.** That could be waivers or quarterly billing. No fees were invented.
- **The trading-day calendar ignores market holidays**, about 9 to 10 days a year.
- **$10.9M of transactions (0.07%) sit in quarantine** until operations identifies their clients.

AI-assisted report — reviewed for factual accuracy on October 19, 2026 by Amon Tadepalli
