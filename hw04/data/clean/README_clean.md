# Wildcat Capital: Clean Extract
Produced by `hw04/scripts/02_clean.py` from the 8 raw files. Same file names and columns as raw, plus three 0/1 flag columns. Raw files were not modified.

| File | Rows | Change vs raw |
|---|---:|---|
| dim_advisor.csv | 25 | none |
| dim_benchmark.csv | 8 | none |
| dim_client.csv | 2,500 | 25 near-duplicates quarantined; 78 states standardized |
| dim_date.csv | 1,827 | none |
| dim_security.csv | 500 | none |
| fact_fees.csv | 122,197 | none |
| fact_portfolio_snapshot.csv | 129,547 | 300 return_ytd values converted; `aum_floor_flag` added |
| fact_transactions.csv | 298,572 | 200 orphan rows quarantined; security_id converted; 835 share signs fixed; 2 flags added |

Audit trail: `../audit/cleaning_log.csv`, `../audit/value_changes.csv`, `../audit/quarantine_*.csv`.

## Relationships
All many-to-one, single direction (dimension filters fact).

| From (many) | To (one) | Notes |
|---|---|---|
| dim_client.advisor_id | dim_advisor.advisor_id | snowflake: client belongs to advisor |
| dim_security.benchmark_id | dim_benchmark.benchmark_id | snowflake |
| fact_fees.client_id | dim_client.client_id | |
| fact_fees.advisor_id | dim_advisor.advisor_id | redundant with client's advisor (always equal) |
| fact_portfolio_snapshot.client_id | dim_client.client_id | |
| fact_portfolio_snapshot.advisor_id | dim_advisor.advisor_id | redundant with client's advisor |
| fact_portfolio_snapshot.benchmark_id | dim_benchmark.benchmark_id | |
| fact_transactions.client_id | dim_client.client_id | |
| fact_transactions.advisor_id | dim_advisor.advisor_id | redundant with client's advisor |
| fact_transactions.security_id | dim_security.security_id | blank on cash transactions (by design) |
| fact_fees.fee_date | dim_date.date | |
| fact_portfolio_snapshot.snapshot_date | dim_date.date | |
| fact_transactions.txn_date | dim_date.date | |

In Power BI, having both a direct advisor_id and a path through dim_client creates ambiguous filter paths. Keep one active (fact to dim_advisor) or route advisor through dim_client.

## Column types for a BI tool
| Type | Columns |
|---|---|
| **Text (do not auto-detect)** | dim_client.zip_code (leading zeros), dim_advisor.certifications (`None` is a value, not null), all name / code columns |
| Whole number | all `*_id` keys, age, years_experience, aum_target_mm, year, quarter, month, week_of_year |
| Decimal | initial_aum, aum, aum_basis, bps_charged, amount, shares, price, expense_ratio_bps, return_ytd, benchmark_return_ytd, active_alpha_ytd, cash_pct |
| Date | client_since, date, fee_date, snapshot_date, txn_date (all YYYY-MM-DD) |
| True/False | dim_client.is_active, dim_security.is_etf |
| 0/1 whole number | dim_date.is_* columns and the three flag columns |

Return and percentage columns are fractions (0.0928 = 9.28%). Format as percent; don't multiply by 100. Some small values are written in scientific notation (`9.9e-05`) and parse as decimals.

## Flag columns added
| Column | Table | Rows = 1 | Meaning |
|---|---|---:|---|
| non_trading_day_flag | fact_transactions | 40,630 | Buy or Sell dated on a day dim_date marks as non-trading (weekends). Date kept; true trade date unknown. |
| after_last_snapshot_flag | fact_transactions | 2,410 | Transaction in a month after the client's last snapshot. All belong to inactive clients. |
| aum_floor_flag | fact_portfolio_snapshot | 420 | AUM exactly 1,000.00, a system floor rather than a real balance (92 clients). |

## Known limitations (chosen not to fix)
| Limitation | Rows | Why not fixed |
|---|---:|---|
| Blank risk_profile | 75 clients | Benchmark 3 looks like a default, so filling "Balanced" would be circular. |
| Advisory Fee transactions don't match fact_fees | 35,742 txns | No client-month agrees (median ratio 3.11x per client-month). Use fact_fees for fee revenue. |
| Sells exceed the position built from earlier Buys | 42,975 sells | No opening holdings in the extract. Use snapshots for positions. |
| return_ytd above 100% | 977 snapshots | Internally consistent and continuous; can't prove wrong. Outliers marked in Part D. |
| Snapshot months with no fee row | 7,350 | Could be waivers or quarterly billing; inventing fees would invent revenue. |
| First snapshot AUM >50% away from initial_aum | 4 clients | Onboarding figure vs later balance; no evidence which is wrong. |
| is_trading_day ignores market holidays | about 9 to 10 days a year | Fixing needs an outside holiday calendar. |
| Converted percent returns keep 4 decimals | 300 | Original text had 2-decimal percents (gap to alpha + benchmark at most 0.00005). |
| Orphan transactions removed | 200 ($10,888,495.37) | Client unknown; kept in quarantine for operations to resolve. |
