# HW6 Measure Library: Wildcat Capital AUM & Performance
MIS3060 Business Intelligence with AI | Amon Tadepalli

All measures live in the `_Measures` table of `powerbi/hw06.pbix`. Every value below is reconciled to pandas in `reports/measure_reconciliation.csv`. Quoted numbers are from `reports/pandas_values.csv` and `reports/design_questions.txt`.

**Additivity patterns used**
- **SUM:** additive, safe across every dimension.
- **Last balance:** semi-additive. `aum` is a balance, so take it at the last snapshot date with data in the current filter (`LASTNONBLANK`, since snapshots are dated the 1st of the month).
- **Recompute-and-weight:** non-additive. Rebuild the ratio from additive parts (or weight it by `aum`) in every filter context; never sum or average the ratio itself.

## Part A: Measures

### Base measures (from the ICEs)
```DAX
Total Fees = SUM ( fact_fees[amount] )

Net Flows =
CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Deposit" )
    - CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Withdrawal" )
```
Pattern: SUM. Format: currency.

### 0. AUM (naive SUM): wrong on purpose
```DAX
AUM (naive SUM) = SUM ( fact_portfolio_snapshot[aum] )
```
- **Pattern:** SUM applied to a balance, which is the mistake. Format: currency.
- **Meaning:** none. With no filter it shows $566.7B, about 45 times the real $12.7B, because it adds 60 monthly balances together. It is kept only to prove the trap and is not on the report page.

### 1. Ending AUM
```DAX
Ending AUM =
CALCULATE (
    SUM ( fact_portfolio_snapshot[aum] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)
```
- **Pattern:** last balance. Format: currency.
- **Meaning:** how much Wildcat manages at the end of the period in view ($12.73B at December 2024).

### 2. Ending Clients
```DAX
Ending Clients =
CALCULATE (
    DISTINCTCOUNT ( fact_portfolio_snapshot[client_id] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)
```
- **Pattern:** last balance (a headcount is a point-in-time stock, like AUM). Format: whole number.
- **Meaning:** how many clients hold an account at the end of the period (2,325), not how many ever did (2,500).

### 3. Avg AUM per Client
```DAX
Avg AUM per Client = DIVIDE ( [Ending AUM], [Ending Clients] )
```
- **Pattern:** recompute (a ratio of two last-balance measures). Format: currency.
- **Meaning:** the size of a typical relationship at period end ($5.48M firm-wide; $383K Retail vs $39.5M UHNW in 2024).

### 4. Ending AUM LY and AUM YoY %
```DAX
Ending AUM LY = CALCULATE ( [Ending AUM], SAMEPERIODLASTYEAR ( dim_date[date] ) )

AUM YoY % = DIVIDE ( [Ending AUM] - [Ending AUM LY], [Ending AUM LY] )
```
- **Pattern:** last balance, time-shifted; YoY is a recompute. `LASTNONBLANK` runs inside the shifted dates, so a 2024 row compares December 2024 with December 2023. Formats: currency, %.
- **Meaning:** how much the book grew over a year (19.58% in 2024). 2020 is blank, not 0%, because there is no 2019 to compare with.

### 5. Ending AUM PM and AUM MoM %
```DAX
Ending AUM PM = CALCULATE ( [Ending AUM], DATEADD ( dim_date[date], -1, MONTH ) )

AUM MoM % = DIVIDE ( [Ending AUM] - [Ending AUM PM], [Ending AUM PM] )
```
- **Pattern:** last balance, shifted one month; MoM is a recompute. Formats: currency, %.
- **Meaning:** the month's change in assets (December 2024: +4.25%, from $12.21B to $12.73B), a short-term read on markets and flows.

### 6. Avg Monthly AUM
```DAX
Avg Monthly AUM =
DIVIDE (
    SUM ( fact_portfolio_snapshot[aum] ),
    DISTINCTCOUNT ( fact_portfolio_snapshot[snapshot_date] )
)
```
- **Pattern:** recompute (an additive sum over balances divided by the number of months, so the summing error cancels). Format: currency.
- **Meaning:** the average balance Wildcat carried during the period ($11.29B in 2024), the right base for revenue that accrues all year.

### 7. Fee Yield (bps)
```DAX
Fee Yield (bps) = DIVIDE ( [Total Fees] * 12 * 10000, SUM ( fact_portfolio_snapshot[aum] ) )
```
- **Pattern:** recompute-and-weight across **two fact tables**. Both filter through the shared `dim_date` and `dim_client`. Monthly fees × 12 ÷ summed monthly AUM gives an annual rate weighted by AUM. Format: decimal, 2 places.
- **Meaning:** what Wildcat earns per dollar it manages (43.15 bps in 2024); Retail pays 82.8 bps vs UHNW 36.1 bps.

### 8. Organic Growth Rate
```DAX
Organic Growth Rate = DIVIDE ( [Net Flows], [Ending AUM LY] )
```
- **Pattern:** recompute (an additive flow over a last balance). Format: %.
- **Meaning:** growth from net new client money alone, before markets (0.73% in 2024, against 19.58% total growth). At the grand total it divides five years of flows by the December 2023 balance, so read it by year.

### 9. AUM-Weighted Alpha
```DAX
AUM-Weighted Alpha =
VAR LastSnap =
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
RETURN
    CALCULATE (
        DIVIDE (
            SUMX (
                fact_portfolio_snapshot,
                fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd]
            ),
            SUM ( fact_portfolio_snapshot[aum] )
        ),
        LastSnap,
        fact_portfolio_snapshot[is_return_suspect] = 0
    )
```
- **Pattern:** recompute-and-weight, at the last balance date. Format: %.
- **Meaning:** how much the average managed dollar beat its benchmark year-to-date (+1.45% in 2024), net of rows with untrustworthy returns.

### 10. Alpha Signal
```DAX
Alpha Signal =
VAR a = [AUM-Weighted Alpha]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( a ), BLANK (),
        a >= 0.02, "Outperforming",
        a <= -0.02, "Lagging",
        "In line"
    )
```
- **Pattern:** inherits measure 9 (text label, not aggregated). Format: text.
- **Meaning:** a plain-English flag for whether a slice of the book is beating its benchmarks by 2 points or more (2022 and 2024 Retail: "Outperforming"; everything else "In line").

### 11. Top 10 Client Share
```DAX
Top 10 Client Share =
VAR LastSnap =
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
VAR Top10 =
    TOPN (
        10,
        VALUES ( dim_client[client_id] ),
        CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), LastSnap )
    )
RETURN
    DIVIDE (
        CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), LastSnap, KEEPFILTERS ( Top10 ) ),
        CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), LastSnap )
    )
```
- **Pattern:** last balance, then a ratio (recompute). `VALUES ( dim_client[client_id] )` keeps the ranking inside the current filter, so in the tier table each tier ranks only its own clients. Clients are ranked at the filter's last snapshot date, not at their own last date, so a departed client can never enter the top 10. Format: %.
- **Meaning:** concentration risk: the 10 largest relationships hold 6.16% of the firm's assets, and 8.13% of UHNW assets.

### Report page
`hw06.pbix` → page **Measures**: cards (Ending AUM, Ending Clients, Avg AUM per Client, Top 10 Client Share); a table by `dim_date[year]`; a table by `dim_client[client_tier]` with a visual-level filter `dim_date[year] = 2024`. `AUM (naive SUM)` is not on the page.

## Part C: Design questions

### (a) Ending AUM vs SUMX over clients
| | Value |
|---|---:|
| `Ending AUM` (no filter) | $12,729,572,078.86 |
| `SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )` | $13,149,297,713.80 |
| Difference | **$419,725,634.94** |

`Ending AUM` finds one last date for the whole firm (2024-12-01) and sums every balance on it. Inside `SUMX`, context transition evaluates `[Ending AUM]` once per client, so `LASTNONBLANK` finds **each client's own** last snapshot. The 2,325 current clients land on 2024-12-01 either way. The other 175 clients left between December 2022 and November 2023. SUMX still adds their final balances, which total exactly $419,725,634.94: money Wildcat no longer manages. `Ending AUM` answers "How much do we manage today?"; the SUMX version mixes today's balances with balances from clients who have left.

### (b) Why 2024 Fee Yield (43.15 bps) is below Effective Fee Rate (45.53 bps)
Both divide the same $48,714,005.93 of 2024 fees, so the cause is the denominator. pandas evidence (`scripts/02_design_questions.py`):
- 2024 has 27,900 snapshot rows but only 26,216 fee rows. **1,684 client-months have a balance but no fee row**, holding $7.07B (5.22% of 2024 snapshot AUM).
- On the 26,216 matched rows, `aum_basis` equals snapshot `aum` on every row (0 differences).
- Recomputing Fee Yield over billed snapshot rows only gives 45.5323 bps, exactly the Effective Fee Rate.

So Fee Yield spreads fees over assets that were never billed, while Effective Fee Rate only counts billed assets. **The data limitation:** `fact_fees` does not cover every client-month. It is missing in every year (1,139 to 1,684 rows a year), across all tiers and 1,082 clients in 2024. The data cannot tell us whether those months were waived, billed outside this table, or lost in the extract. Fee Yield is the honest firm-level number (revenue per dollar actually managed). Effective Fee Rate is the price charged to billed accounts.

### (c) AUM-Weighted Alpha: last snapshot, no suspects
- **Last snapshot only:** `active_alpha_ytd` is year-to-date, so each month already contains every earlier month. December holds the full-year result. Averaging January to December mixes 1-month and 12-month windows and counts early months many times. Weighting all of 2024's rows gives 0.32% instead of 1.45%. Also, `aum` is a balance, so only one date's balances form a valid weight.
- **Exclude `is_return_suspect = 1`:** 148 of the 2,325 December 2024 rows are flagged. Their alphas run from -120.9% to +7,133.8% (median +53.6%), which are data errors, not performance.

| At 2024-12-01 | Value |
|---|---:|
| AUM-weighted, suspects excluded (**the measure**) | **1.448%** |
| Simple mean, same 2,177 rows | 0.879% |
| AUM-weighted, suspects included | 1.668% |
| Simple mean, suspects included (for reference) | 15.56% |

Weighting matters: the weighted figure is higher than the simple mean, so larger accounts beat their benchmarks by more than small ones. Suspects matter too. They hold only $15.5M of AUM, yet they lift the weighted alpha by 0.22 points and inflate a simple mean to a meaningless 15.6%.

### (d) Organic growth by tier, 2024
| Tier | Net flows | Organic Growth | AUM YoY % | AUM change not from flows |
|---|---:|---:|---:|---:|
| Retail | $44.2M | **9.87%** | 19.13% | $41.5M |
| HNW | $25.2M | 1.18% | 19.64% | $393.1M |
| UHNW | $8.1M | 0.10% | 19.59% | $1,572.5M |

**What it says:** all three tiers grew about 19.5%, but for different reasons. Retail is the only tier where client money drives growth (about half its increase). HNW and UHNW grew almost entirely from market returns on existing assets: UHNW added $1.58B with only $8.1M of net new money. Wildcat's net new money comes mostly from Retail. Its dollar growth comes from markets acting on the large HNW/UHNW book, so its revenue is highly exposed to a market downturn.

**What it does not tell you:**
- How much of the non-flow growth is the market versus Wildcat's skill (alpha) or fees debited.
- Whether flows come from new or existing clients. In 2024 no client joined or left, so it is all existing clients.
- Whether the flows will persist.
- Anything about the $62.2M of "Advisory Fee" debits, which reduce AUM but are not in Net Flows.

A tier's organic rate is also relative to its own size. Retail's 9.87% is only $44M, about 2% of the year's total AUM increase.
