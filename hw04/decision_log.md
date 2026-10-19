# HW4 Decision Log
MIS3060 Business Intelligence with AI | Amon Tadepalli

Each entry was written from the Part A audit (`reports/dq_summary_raw.csv`) before any cleaning code existed, and is the instruction Claude Desktop used to draft that step of `02_clean.py`. Entries cover defects I fix, values I flag, and structures I decided are legitimate and left alone.

Dimensions: Validity, Completeness, Uniqueness, Consistency, Accuracy/Plausibility, Referential Integrity

**Summary**

| ID | Table / column | Decision |
|---|---|---|
| D01 | dim_client / client_id (near-duplicates) | quarantine |
| D02 | dim_client / state | standardize |
| D03 | dim_client / risk_profile | leave as is |
| D04 | dim_client / zip_code | leave as is |
| D05 | dim_advisor / certifications | leave as is |
| D06 | dim_security / sector, expense_ratio_bps | leave as is |
| D07 | dim_security / name | leave as is |
| D08 | dim_date / is_trading_day | leave as is |
| D09 | fact_transactions / security_id | convert |
| D10 | fact_transactions / client_id (orphans) | quarantine |
| D11 | fact_transactions / shares (negative Buys) | convert |
| D12 | fact_transactions / security_id, shares, price (blank on cash txns) | leave as is |
| D13 | fact_transactions / txn_date (weekend trades) | flag |
| D14 | fact_transactions / txn_date (after last snapshot) | flag |
| D15 | fact_transactions / amount (Advisory Fee vs fact_fees) | leave as is |
| D16 | fact_transactions / shares (sells exceed position) | leave as is |
| D17 | fact_portfolio_snapshot / return_ytd (% text) | convert |
| D18 | fact_portfolio_snapshot / return_ytd, active_alpha_ytd (scientific notation) | leave as is |
| D19 | fact_portfolio_snapshot / aum (1,000.00 floor) | flag |
| D20 | fact_portfolio_snapshot / return_ytd (above 100%) | leave as is |
| D21 | fact_portfolio_snapshot / snapshot_date (months with no fee) | leave as is |

**Cleaning order.** Dimensions before facts, so referential checks on the facts run against a final set of keys. Inside each table: type conversions first (a value has to parse before a rule can test it), then quarantines, then value fixes, then flags. D01 runs before D10 so the orphan test uses the de-duplicated client list.

---

## D01: Near-duplicate clients
| Field | Entry |
|---|---|
| **Table / column** | dim_client / client_id (rows 2501 to 2525) |
| **Evidence** | 25 rows match an earlier client on all 12 other fields (name, age, city, state, zip, risk, tier, account type, initial_aum to the cent, client_since, advisor, is_active). Only the last name differs by one letter: 23 lose the last letter (674 Taylor / 2501 Taylo), 2 gain one (1193 Lee / 2512 Leen). None of the 25 IDs appear in fact_fees, fact_portfolio_snapshot or fact_transactions. |
| **Dimension violated** | Uniqueness |
| **Decision** | quarantine |
| **Justification** | Same person entered twice with a typo. Keeping them inflates the client count (2,525 instead of 2,500) and drags down averages like AUM per client. Because no fact row points at them, removing them breaks no joins. Verify: assert no fact row references a quarantined ID, and that every quarantined row has a match in the kept set. |
| **Risk** | If any are real, separate people, we undercount clients by up to 25. Financial totals are unaffected because they have no activity. |

## D02: State names instead of codes
| Field | Entry |
|---|---|
| **Table / column** | dim_client / state |
| **Evidence** | 78 of 2,525 rows (3.1%) fail the 2-letter code list: Pennsylvania 25, Florida 15, New York 14, New Jersey 13, California 5, Illinois 4, Texas 2. Every one of those states also appears in code form. |
| **Dimension violated** | Validity, Consistency |
| **Decision** | standardize |
| **Justification** | A state map or slicer would show "PA" and "Pennsylvania" as two places. Map the seven names to USPS codes. Verify: after the fix, 100% of values are in the allowed list and the per-state counts equal code count + name count. |
| **Risk** | Very low. The mapping is one-to-one and limited to the seven names seen. |

## D03: Blank risk profile
| Field | Entry |
|---|---|
| **Table / column** | dim_client / risk_profile |
| **Evidence** | 76 blanks (3.0%), spread across tiers (49 Retail, 18 HNW, 9 UHNW) and mostly active (72). All 76 sit on benchmark 3 (60/40 Blend) in every one of their 3,942 snapshots. |
| **Dimension violated** | Completeness |
| **Decision** | leave as is |
| **Justification** | Tempting to fill "Balanced" because benchmark 3 is the Balanced benchmark, but that is circular: benchmark 3 looks like the default the system assigns when no profile exists. Filling would invent a suitability answer the client never gave. Leave blank and list it as a known limitation, so the committee sees 76 clients with no risk assessment on file. |
| **Risk** | Risk-profile reports show a "(Blank)" bucket. If the benchmark really was chosen on purpose, we left a recoverable value unfilled. |

## D04: Zip codes with leading zeros
| Field | Entry |
|---|---|
| **Table / column** | dim_client / zip_code |
| **Evidence** | 100% of 2,525 values are 5 digits. Many start with 0 (client 2: 03897). |
| **Dimension violated** | none (risk is to Validity if parsed as a number) |
| **Decision** | leave as is |
| **Justification** | Legitimate structure. Read as a number, 03897 becomes 3897, which is why the brief says to read as text. Keep as text and tell the BI tool to type it as text. |
| **Risk** | None if typed as text downstream. |

## D05: "None" in certifications
| Field | Entry |
|---|---|
| **Table / column** | dim_advisor / certifications |
| **Evidence** | 6 of 25 advisors have the text `None`. The profiler flags it as a null-like word. |
| **Dimension violated** | none |
| **Decision** | leave as is |
| **Justification** | Means "holds no certification", which is a real answer, not missing data. Default pandas parsing would turn it into NaN and wrongly report 6 missing values. |
| **Risk** | A BI tool may also read `None` as null. Documented in README_clean.md. |

## D06: Blank sector and expense ratio
| Field | Entry |
|---|---|
| **Table / column** | dim_security / sector, expense_ratio_bps |
| **Evidence** | Sector blank on exactly the 219 ETFs; expense ratio blank on exactly the 281 non-ETFs. Zero exceptions either way. |
| **Dimension violated** | none |
| **Decision** | leave as is |
| **Justification** | Legitimate structure: a stock has a sector but no expense ratio, and these ETFs are diversified funds with an expense ratio but no single sector. Filling either would be invented data. |
| **Risk** | Sector charts show a "(Blank)" bar for ETFs. Label it "ETF / multi-sector" in the visual, not in the data. |

## D07: Duplicate security names
| Field | Entry |
|---|---|
| **Table / column** | dim_security / name |
| **Evidence** | 3 names appear twice (Jones Inc Fund, Davis PLC Fund, Graham Group Inc.). Each pair has different tickers and a different asset class or sector. Ticker is 100% unique. |
| **Dimension violated** | none |
| **Decision** | leave as is |
| **Justification** | Different instruments that happen to share an issuer name. Ticker and security_id are the real identifiers. |
| **Risk** | A visual grouped by name would merge two securities. Use ticker as the display key. |

## D08: Trading-day flag ignores holidays
| Field | Entry |
|---|---|
| **Table / column** | dim_date / is_trading_day |
| **Evidence** | Every other attribute agrees with the date, and the calendar has no gaps. But is_trading_day = 1 for all 1,305 weekdays, including holidays like Christmas on a weekday (3 cases in 2020 to 2024). |
| **Dimension violated** | Accuracy |
| **Decision** | leave as is |
| **Justification** | It is a simplified calendar, not a broken one. Adding an exchange holiday list would bring in outside data. Documented as a limitation. |
| **Risk** | Trading-day counts are overstated by about 9 to 10 days a year. |

## D09: security_id stored as a decimal
| Field | Entry |
|---|---|
| **Table / column** | fact_transactions / security_id |
| **Evidence** | All 197,175 non-blank values look like `45.0`; dim_security uses `45`. As text, 0% of transactions join to dim_security. After removing `.0`, every key matches. |
| **Dimension violated** | Validity, Referential Integrity |
| **Decision** | convert |
| **Justification** | Classic float artifact from a column that had blanks. The relationship to dim_security is unusable until fixed. Convert only values matching `^\d+\.0$`; assert none have a nonzero decimal. |
| **Risk** | None: every value ends in `.0`, so no information is lost. |

## D10: Transactions for clients that do not exist
| Field | Entry |
|---|---|
| **Table / column** | fact_transactions / client_id |
| **Evidence** | 200 rows reference 200 distinct client IDs (2702 to 3192) missing from dim_client. They total $10,888,495.37, 0.07% of transaction dollars, across all six txn types. |
| **Dimension violated** | Referential Integrity |
| **Decision** | quarantine |
| **Justification** | There is no key, name or other field to tell us which real client these belong to. Reassigning them would be guessing. Moving them to a quarantine file keeps them traceable for the operations team. |
| **Risk** | If these clients exist in a source system we were not given, we understate activity by about $10.9M. Small against the total, and recoverable from the quarantine file. |

## D11: Negative shares on Buys
| Field | Entry |
|---|---|
| **Table / column** | fact_transactions / shares |
| **Evidence** | 836 Buys (1.0% of 83,556) have negative shares. For all 836, amount is positive and equals \|shares\| x price to the cent. All 59,755 Sells and 53,864 Dividends have positive shares. Spread across 692 clients and all five years (not one bad batch). |
| **Dimension violated** | Validity, Consistency |
| **Decision** | convert |
| **Justification** | The amount and price prove the trade size; only the sign is wrong. The table records direction in txn_type, not the sign of shares, so Buy shares must be positive. Take the absolute value. Verify: assert amount = shares x price for 100% of security transactions after the fix. |
| **Risk** | If the negative sign actually meant "this was a Sell mislabeled as Buy", the fix keeps the wrong direction. The amount gives no way to tell, so I keep txn_type as recorded and note it. |

## D12: Blank security fields on cash transactions
| Field | Entry |
|---|---|
| **Table / column** | fact_transactions / security_id, shares, price |
| **Evidence** | 101,597 rows (34.0%) blank on all three. Every one is a Deposit, Withdrawal or Advisory Fee; every Buy, Sell and Dividend has all three. Same finding as HW2. |
| **Dimension violated** | none |
| **Decision** | leave as is |
| **Justification** | Legitimate structure: a cash movement has no security. Filling with 0 would make shares and price averages wrong. |
| **Risk** | The security relationship in Power BI will show blanks for cash rows. Expected. |

## D13: Trades on non-trading days
| Field | Entry |
|---|---|
| **Table / column** | fact_transactions / txn_date |
| **Evidence** | 40,649 Buys and Sells (28.4% of 143,311 trades) fall on a day dim_date marks as non-trading (weekends). |
| **Dimension violated** | Accuracy/Plausibility |
| **Decision** | flag (`non_trading_day_flag`) |
| **Justification** | Exchanges are closed on weekends, so these dates are probably booking dates, not trade dates. The true trade date can't be recovered, and shifting to the next Monday would invent data. The share is too large to quarantine. A flag lets an analyst exclude them from day-level work and keep them in monthly totals. Deposits, withdrawals and fees are not flagged; posting those on a weekend is plausible. |
| **Risk** | Day-of-week analysis is unreliable for flagged trades. Monthly totals are unaffected unless a trade sits on a month boundary. |

## D14: Activity after a client's account stops reporting
| Field | Entry |
|---|---|
| **Table / column** | fact_transactions / txn_date |
| **Evidence** | 2,410 transactions fall in a month after the client's last snapshot. All belong to inactive clients (176 inactive in total), and include Buys (689) and Deposits (278), not just closing withdrawals. |
| **Dimension violated** | Consistency (cross-table) |
| **Decision** | flag (`after_last_snapshot_flag`) |
| **Justification** | Buying securities in a closed account is implausible, but late postings or wind-down activity are possible. No account close date exists to settle it. Flag so AUM reconciliations can exclude them. |
| **Risk** | If they are real, excluding them understates final-period activity; if not, including them overstates it. The flag leaves the choice visible. |

## D15: Advisory Fee transactions don't match fact_fees
| Field | Entry |
|---|---|
| **Table / column** | fact_transactions / amount (txn_type = Advisory Fee) vs fact_fees / amount |
| **Evidence** | 0 of 28,746 client-months that appear in both tables agree. Median ratio of transaction debits to fee charges is about 2.8x. |
| **Dimension violated** | Consistency (cross-table) |
| **Decision** | leave as is |
| **Justification** | The two come from different systems and appear to measure different things (fee debits from cash vs billed charges). fact_fees reconciles exactly to aum_basis x bps / 12 and to snapshot AUM, so it is the trustworthy source for fee revenue. I can't say which transaction rows are wrong, so I change nothing and document that fee revenue should come from fact_fees. |
| **Risk** | Anyone who sums Advisory Fee transactions as revenue will get a number about 2.8x too high. |

## D16: Sells larger than the position
| Field | Entry |
|---|---|
| **Table / column** | fact_transactions / shares |
| **Evidence** | Running Buy minus Sell per client and security goes negative on 43,010 of 59,755 Sells. |
| **Dimension violated** | Consistency (within table) |
| **Decision** | leave as is |
| **Justification** | The extract has no opening holdings as of 2020, so a Sell of shares bought before 2020 looks like an oversell. This is a missing-context limitation, not a row defect. |
| **Risk** | Holdings can't be rebuilt from transactions alone. Use fact_portfolio_snapshot for positions. |

## D17: Returns stored as percent text
| Field | Entry |
|---|---|
| **Table / column** | fact_portfolio_snapshot / return_ytd |
| **Evidence** | 300 values are text like `9.28%` (0.23%); the rest are decimals like `0.0928`. For all 300, value / 100 equals active_alpha_ytd + benchmark_return_ytd within 0.00005 (the rounding of a 2-decimal percent). Example: snapshot 42 shows `9.28%`; alpha 0.009966 + benchmark 0.08279 = 0.092756. |
| **Dimension violated** | Validity, Consistency |
| **Decision** | convert |
| **Justification** | Strip `%` and divide by 100. Reconciling against alpha + benchmark proves the reading (it is 9.28%, not 928%). Verify: assert every converted value is within 0.00006 of alpha + benchmark. |
| **Risk** | The converted values keep only 4 decimals of precision (0.0928 vs 0.092756), a difference of under 0.005 percentage points. Noted in the value-change log. |

## D18: Scientific notation in return columns
| Field | Entry |
|---|---|
| **Table / column** | fact_portfolio_snapshot / return_ytd (135), active_alpha_ytd (756) |
| **Evidence** | Values like `9.9e-05` alongside regular decimals. All parse as numbers. |
| **Dimension violated** | none |
| **Decision** | leave as is |
| **Justification** | A valid way to write a very small number. Power BI and pandas both read it correctly as decimal. Rewriting the text would change nothing. |
| **Risk** | Someone reading the CSV in a text editor may find it odd. None for analysis. |

## D19: AUM stuck at $1,000.00
| Field | Entry |
|---|---|
| **Table / column** | fact_portfolio_snapshot / aum |
| **Evidence** | 420 snapshots across 92 clients show exactly 1,000.00, repeated month after month, with return_ytd near -96%. 386 fee rows were billed on that 1,000.00 aum_basis. |
| **Dimension violated** | Accuracy/Plausibility |
| **Decision** | flag (`aum_floor_flag`) |
| **Justification** | An identical balance to the cent for several months while markets move is a system floor, not a real balance. The true AUM can't be recovered, and quarantining would leave holes in monthly series. The flag lets AUM totals and return analysis exclude them. |
| **Risk** | Fees billed on a $1,000 basis are under $1 a month each, so the revenue effect is negligible. The bigger risk is extreme negative returns in performance averages if the flag is ignored. |

## D20: Returns above 100%
| Field | Entry |
|---|---|
| **Table / column** | fact_portfolio_snapshot / return_ytd |
| **Evidence** | 976 numeric values have \|return_ytd\| > 1 (max 94.67, i.e. +9,467%), across 144 clients. Alpha still reconciles to return minus benchmark, and the values move smoothly month to month (client 1003: 0.97, 1.00, 1.05, 1.07). Median AUM for these rows is about $72k vs $485k overall. |
| **Dimension violated** | Accuracy/Plausibility |
| **Decision** | leave as is (IQR flag in Part D) |
| **Justification** | Unlike D17, these are not a format error: they are internally consistent and continuous. Small accounts with large deposits can show huge percentage swings when deposits aren't separated from return. I can't prove them wrong, so I leave them and let Part D mark outliers. |
| **Risk** | Average return by advisor or tier will be skewed. Use medians or exclude outliers in Assignment 5. |

## D21: Snapshot months with no fee
| Field | Entry |
|---|---|
| **Table / column** | fact_portfolio_snapshot / snapshot_date vs fact_fees |
| **Evidence** | 7,350 snapshots (5.7%) have no fee row for that client-month, spread across 2,261 clients (median 3 months each). The reverse never happens: every fee row has a snapshot with the same AUM. |
| **Dimension violated** | Completeness (possible) |
| **Decision** | leave as is |
| **Justification** | A fee not billed every month is plausible (waivers, quarterly billing, timing). Nothing points to which rows are missing, and creating fee rows would invent revenue. |
| **Risk** | If these are lost fee records, fee revenue is understated. Noted as a limitation. |
