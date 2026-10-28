# HW5 Star Design: Wildcat Capital
MIS3060 Business Intelligence with AI | Amon Tadepalli

## Part A: Keys

| Table | Type | Primary key | Foreign keys (column → table[column]) |
|---|---|---|---|
| dim_advisor | Dimension | `advisor_id` | — |
| dim_benchmark | Dimension | `benchmark_id` | — |
| dim_client | Dimension | `client_id` | `advisor_id` → dim_advisor[advisor_id] |
| dim_date | Dimension | `date_id` | — |
| dim_security | Dimension | `security_id` | `benchmark_id` → dim_benchmark[benchmark_id] |
| fact_fees | Fact | `fee_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`fee_date` → dim_date[date] |
| fact_portfolio_snapshot | Fact | `snapshot_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`benchmark_id` → dim_benchmark[benchmark_id]<br>`snapshot_date` → dim_date[date] |
| fact_transactions | Fact | `txn_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`security_id` → dim_security[security_id] *(can be blank)*<br>`txn_date` → dim_date[date] |

**Keys that can legitimately be blank:** only `fact_transactions[security_id]`, on 101,528 rows. Every one is a Deposit, Withdrawal or Advisory Fee: cash moving in or out of the account, so there is no security to point to. No Buy, Sell or Dividend row is blank, and no cash row carries a security.

**Proof:** `scripts/01_keys_grain.py` checks all 8 primary keys (unique, never blank) and all 13 foreign keys (0 orphans). It also shows the fact dates match `dim_date[date]` on every row and `dim_date[date_id]` on none. 63 checks pass, 0 fail, plus 2 info counts (`reports/key_checks.csv`).

## Part B: Grain

- **fact_fees:** One row represents the fee charged to one client for one month.
- **fact_portfolio_snapshot:** One row represents one client's account position for one month (each snapshot is dated the 1st of its month).
- **fact_transactions:** One row represents a single transaction (trade, dividend, deposit, withdrawal or advisory fee debit) on one client's account.

**Proof:** `client_id + fee_date` and `client_id + snapshot_date` have 0 duplicates, and every fee and snapshot date is the 1st of a month. The date is a month label rather than a start-of-month reading: January snapshots already carry year-to-date returns (median 0.7%), so each row reflects that month's position. Transactions have no natural key: `client_id + txn_date + security_id + txn_type` repeats 622 times (for example, two buys of the same stock on the same day). That means `txn_id` is the only column that makes a transaction row unique.

## Part C: Measures

### Fact measures
| Table | Column | Type | How it may be summed or averaged |
|---|---|---|---|
| fact_fees | `amount` | Additive | Fee dollars sum across clients, advisors and months: the total is fees billed for that slice. |
| fact_fees | `aum_basis` | Semi-additive | A month-start balance (it equals that client's snapshot `aum` exactly), so it sums across clients within one month but never across months; use the latest month or the monthly average over time. |
| fact_fees | `bps_charged` | Non-additive | A rate that is never summed and should not be plainly averaged either, because `amount = aum_basis × bps / 10,000 / 12` on every row, so the true rate for any group is `SUM(amount) / SUM(aum_basis) × 12 × 10,000`. |
| fact_portfolio_snapshot | `aum` | Semi-additive | A balance that sums across clients, advisors and accounts at one date, but adding January to February double counts the same money, so over time take the last month (or the average). |
| fact_portfolio_snapshot | `return_ytd` | Non-additive | A cumulative percentage that resets each January, so it cannot be summed across months or clients; across clients use an AUM-weighted average at one date, and the December row is the year's return. |
| fact_portfolio_snapshot | `benchmark_return_ytd` | Non-additive | Same as `return_ytd`: a year-to-date percentage for the client's benchmark, only averaged (weighted) at one point in time. |
| fact_portfolio_snapshot | `active_alpha_ytd` | Non-additive | Return minus benchmark return, so it is never summed and is recomputed from the weighted returns rather than averaged. |
| fact_portfolio_snapshot | `cash_pct` | Non-additive | A share of the account; for a group use the AUM-weighted average (cash dollars ÷ AUM), not a sum or plain mean. |
| fact_transactions | `amount` | Additive | Sums across clients, securities and dates, but every value is positive and the direction lives in `txn_type`, so it must be sliced by `txn_type` (adding a Deposit to a Withdrawal gives gross activity, not net flow). |
| fact_transactions | `shares` | Additive | Shares sum across clients and dates for one security (e.g., shares bought), but adding shares of different securities is meaningless, and the column is blank on cash rows. |
| fact_transactions | `price` | Non-additive | A per-share price on the trade date (blank on cash rows) that is never summed and is averaged only as share-weighted, `SUM(amount) / SUM(shares)` for one security. |

### Numeric columns that are not measures
| Table | Column | Why |
|---|---|---|
| all facts | `fee_id`, `snapshot_id`, `txn_id` | Primary keys: row identifiers. Count them, never sum them |
| all facts | `client_id`, `advisor_id`, `benchmark_id`, `security_id` | Foreign keys: they point to dimensions |
| fact_portfolio_snapshot | `year`, `month` | Date parts that repeat `snapshot_date`; filter with `dim_date` instead |
| fact_portfolio_snapshot | `is_return_suspect` | 0/1 data-quality flag (3,875 rows). A sum gives a count of flagged rows, which is a count, not a measure |
| fact_transactions | `is_post_departure_txn` | 0/1 flag (2,410 rows), same treatment |
| fact_portfolio_snapshot | `account_type` | Looks numeric because `529` is one of its values, but it is a category (Trust, IRA, Roth IRA, Taxable, 529). Load as **Text** in Power BI |

### Numeric dimension attributes that should never be summed
| Table | Column | Why |
|---|---|---|
| dim_advisor | `years_experience` | A trait of the advisor; average it, don't sum |
| dim_advisor | `aum_target_mm` | A target in $ millions per advisor; summing across fact rows repeats it once per row it filters |
| dim_client | `age` | Personal attribute; average or band it |
| dim_client | `initial_aum` | AUM when the client joined, a fixed historical value; summing through a fact relationship would repeat it every month |
| dim_client | `zip_code` | Text code, not a number (load as Text to keep leading zeros) |
| dim_security | `expense_ratio_bps` | A rate; blank for non-ETFs; average only, weighted by holdings |
| dim_date | `year`, `quarter`, `month`, `week_of_year` | Calendar labels for grouping and sorting |
| dim_date | `is_month_end`, `is_quarter_end`, `is_year_end`, `is_trading_day` | 0/1 flags for filtering |

## Part E: Relationships and design questions

### Relationships built
| From (many) | To (one) | Cardinality | Direction | Active | Reason |
|---|---|---|---|---|---|
| fact_fees[client_id] | dim_client[client_id] | *:1 | Single | Yes | Conformed client dimension; filters fees by client attributes (tier, state, risk profile) |
| fact_fees[advisor_id] | dim_advisor[advisor_id] | *:1 | Single | Yes | Direct path so an advisor slicer filters fees without going through dim_client |
| fact_fees[fee_date] | dim_date[date] | *:1 | Single | Yes | Calendar date join (see c) |
| fact_portfolio_snapshot[client_id] | dim_client[client_id] | *:1 | Single | Yes | Conformed client dimension |
| fact_portfolio_snapshot[advisor_id] | dim_advisor[advisor_id] | *:1 | Single | Yes | Direct advisor path (see b) |
| fact_portfolio_snapshot[benchmark_id] | dim_benchmark[benchmark_id] | *:1 | Single | Yes | The client's assigned benchmark for that month |
| fact_portfolio_snapshot[snapshot_date] | dim_date[date] | *:1 | Single | Yes | Calendar date join (see c) |
| fact_transactions[client_id] | dim_client[client_id] | *:1 | Single | Yes | Conformed client dimension |
| fact_transactions[advisor_id] | dim_advisor[advisor_id] | *:1 | Single | Yes | Direct advisor path (see b) |
| fact_transactions[security_id] | dim_security[security_id] | *:1 | Single | Yes | What was traded; blank on cash rows (see a) |
| fact_transactions[txn_date] | dim_date[date] | *:1 | Single | Yes | Calendar date join (see c) |
| dim_security[benchmark_id] | dim_benchmark[benchmark_id] | *:1 | Single | Yes | Snowflake link; no second path, so it can stay active (see d) |
| dim_client[advisor_id] | dim_advisor[advisor_id] | *:1 | Single | **No** | Redundant second path to dim_advisor; kept inactive (see b) |

`dim_date` is marked as the date table on `date`. Row counts in Power BI (COUNTROWS on each table) match the handout: 25, 8, 2,500, 1,827, 500, 122,197, 129,547, 298,572.

**Conformed dimensions:** `dim_client`, `dim_advisor` and `dim_date` are shared by all three fact tables, so one slicer on any of them filters fees, snapshots and transactions together. `dim_benchmark` is shared by two: directly by `fact_portfolio_snapshot`, and by `fact_transactions` through `dim_security`. `dim_security` is used only by `fact_transactions`.

**(a) Blank `security_id` on transactions.** 101,528 transactions have no `security_id`, and every one is a Deposit, Withdrawal or Advisory Fee. These rows move cash in or out of the account, so there is no security to point to; no Buy, Sell or Dividend row is blank, and no cash row carries a security. That makes it expected structure, not a defect: I kept the column as Whole Number with nulls, and the `(Blank)` member it creates on `dim_security` simply groups the cash activity.

**(b) `advisor_id` paths.** `advisor_id` gives two routes to `dim_advisor`: directly from each fact, and through `dim_client`. Power BI allows only one active path, so I kept the three direct fact → `dim_advisor` relationships active and made `dim_client → dim_advisor` inactive. The direct links keep each fact one hop from every dimension (a true star), and `01_keys_grain.py` shows the fact `advisor_id` equals the client's advisor in `dim_client` on every row of all three facts, so the inactive path would return the same answer. Power BI's auto-detect did the opposite (it activated `dim_client → dim_advisor` and deactivated all three fact → `dim_client` links), so I deleted its relationships and built these by hand.

**(c) Date join column.** I joined `fee_date`, `snapshot_date` and `txn_date` to `dim_date[date]`. The facts store calendar dates, and `date_id` is just a 1 to 1,827 row number: the script shows the fact dates match `dim_date[date]` on every row and `date_id` on none. `date` is unique, so it works as the one side, and it is the column I marked as the date table, which time-intelligence functions need in Assignment 6.

**(d) Star or snowflake.** Two links connect one dimension to another: `dim_client → dim_advisor` and `dim_security → dim_benchmark`. I kept both but treated them differently. `dim_client → dim_advisor` is inactive because the facts already reach `dim_advisor` directly. `dim_security → dim_benchmark` is active because it creates no second path (transactions have no `benchmark_id`), and it is the only way to group trades by the benchmark a security tracks. That one active link makes the model a slight snowflake rather than a pure star. One caution: `dim_benchmark` means different things on its two paths (the client's assigned benchmark for snapshots, the security's benchmark for trades), so a benchmark slicer filters the two facts on different logic.

## Part F: Reflection

| Fact table | Business question | Single visual, no DAX workaround? | Schema change if not |
|---|---|---|---|
| fact_fees | Which advisors billed the most fees in 2024, split by fee type? | **Yes.** A stacked bar of `amount` by `dim_advisor[advisor_id]` (with `first_name` and `last_name` in the tooltip, since two advisors are named Johnson) and `fee_type`, filtered to `dim_date[year]` = 2024. Fee `amount` is additive across clients, months and advisors, so the default Sum is correct. | None needed |
| fact_portfolio_snapshot | What was each advisor's AUM at the end of 2024, and how has it grown year over year? | **No.** AUM is semi-additive, so the default Sum on a visual by year adds twelve month-start balances: firm AUM shows as $135.5B for 2024 when the December 2024 snapshot is $12.7B. The date table can't fix it either: snapshots are dated the 1st, so none of them land on a `dim_date` row flagged `is_month_end`, `is_quarter_end` or `is_year_end`. Getting it right needs a DAX measure (`LASTNONBLANK` / `CLOSINGBALANCEYEAR`-style) or a manual month filter on every visual. | Add a period-end flag that matches the snapshots (e.g. `is_last_snapshot_of_quarter` / `_of_year` on the fact, or date snapshots at month end so the existing `dim_date` flags apply) |
| fact_transactions | What were net client flows (deposits minus withdrawals) by advisor each year? | **No.** Every `amount` is positive and the direction lives only in `txn_type`, so Sum of `amount` adds withdrawals to deposits. A visual can show the two side by side, but net flow (2024: $410.5M in, $333.0M out, $77.5M net) needs a measure that subtracts one from the other. | Store a signed amount (or a `flow_sign` of +1 / −1 in a small `dim_txn_type`) so net flow is a plain Sum |

**What the model can and cannot answer.** Anything built on additive dollars (fees billed, trade and dividend volumes, counts of clients or trades) works in one visual today. The model is weakest on the two things a wealth manager asks most: balances over time and net money movement. Both are answerable, but only with DAX that every report author has to remember to use, which is exactly where totals go silently wrong. Returns have the same issue at a smaller scale: `return_ytd` and `cash_pct` need an AUM-weighted average, which is also a DAX measure.
