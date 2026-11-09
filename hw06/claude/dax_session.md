# Part D: Claude session for measure 9 (AUM-Weighted Alpha)
Workflow: **Draft → Test → Debug → Review** (Week 10).
Session: Claude (claude.ai, Claude Opus 5.5), 2026-11-09. The prompt was sent with the three metadata grids from `model_metadata.md`; measures 9 and 10 were removed from the measures grid first, so Claude drafted from scratch.

---

## Prompt 1 (Draft)

> I'm building a DAX measure library in Power BI Desktop for a wealth manager (Wildcat Capital). Below is my model metadata exported with INFO.VIEW.COLUMNS, INFO.VIEW.RELATIONSHIPS and INFO.VIEW.MEASURES. Use only these table and column names. Reuse existing measures where it helps.
>
> *[columns grid, relationships grid and measures grid from `model_metadata.md` pasted here; measures grid without AUM-Weighted Alpha and Alpha Signal]*
>
> **What the metadata can't tell you:**
> - **Grain of `fact_portfolio_snapshot`:** one row per client per month. `snapshot_date` is always the 1st of the month (so `LASTDATE`/`ENDOFMONTH` find no data; my `[Ending AUM]` uses `LASTNONBLANK`). `client_id + snapshot_date` is unique.
> - **`aum` is a balance** (semi-additive): it can be summed across clients on one date, never across months.
> - **`active_alpha_ytd` is a year-to-date rate** (portfolio return minus benchmark return since January 1, as a decimal: 0.02 = 2 points). It resets every January, so December holds the full-year value. It is non-additive.
> - **`is_return_suspect`** is a 0/1 Whole Number flag for rows whose return data failed validation.
> - `dim_date` is marked as the date table (per the assignment), and the report slices by `dim_date[year]` and `dim_client[client_tier]`.
>
> **Business definition (exact):** `AUM-Weighted Alpha` = `active_alpha_ytd` weighted by `aum`, at the last snapshot, excluding `is_return_suspect = 1`. "Last snapshot" means the last snapshot date with data in the current filter context.
>
> Please give me:
> 1. The measure (store it in `_Measures`, format as %).
> 2. An explanation of its filter context: what it returns at the grand total, on a `dim_date[year]` row, and on a `dim_client[client_tier]` row with a 2024 visual filter.
> 3. A DAX test query I can run in DAX query view to check it, including the edge cases you think matter.

---

## Response 1 (Claude, full)

Here's the measure. It follows the same last-balance logic as your `[Ending AUM]`: first find the last snapshot date, then do the weighting only on that date.

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
Format: Percentage, 2 decimals.

**Why it is built this way**
- **`SUMX(aum × alpha) / SUM(aum)`** is the weighted average: each client's alpha counts in proportion to the dollars behind it. `SUMX` is needed because the product has to be computed row by row before summing. `AVERAGE(active_alpha_ytd)` would give a $50K account the same say as a $50M one.
- **`LastSnap` comes first, before the suspect filter.** `LASTNONBLANK` scans the dates visible in the current filter and keeps the last one where `fact_portfolio_snapshot` has rows. Because it runs before the suspect filter is applied, "last snapshot" means the last month with any data, which matches `[Ending AUM]`. The suspect filter then removes rows only within that month.
- **Why only one date:** `active_alpha_ytd` is cumulative. December already contains January through November, so weighting all twelve months together would mix 1-month and 12-month windows and pull the result toward early-year values. And `aum` is a balance, so only balances from a single date form a meaningful weight.
- **`fact_portfolio_snapshot[is_return_suspect] = 0`** is a simple column filter inside `CALCULATE`. It is equivalent to `FILTER ( ALL ( fact_portfolio_snapshot[is_return_suspect] ), … = 0 )`, so it replaces any existing filter on that column, which is what you want. Suspect returns are often extreme, and even a small amount of AUM attached to a huge alpha can move a weighted average.
- **`DIVIDE`** returns BLANK if the denominator is zero or blank, so `[Alpha Signal]` can treat "no data" separately from "in line".

**Filter context, case by case**
| Where it's evaluated | What `LastSnap` resolves to | Rows weighted |
|---|---|---|
| Grand total (no filters) | 2024-12-01, the last snapshot in the whole model | Every non-suspect client on 2024-12-01 |
| `dim_date[year]` = 2022 row | 2022-12-01 | Non-suspect clients on 2022-12-01; their alpha is the full 2022 year-to-date figure |
| `dim_client[client_tier]` = "UHNW" row, visual filter 2024 | 2024-12-01 (the last date in 2024 that has UHNW rows) | Non-suspect UHNW clients on 2024-12-01 |
| A month row, e.g. March 2024 | 2024-03-01 | Alpha is January to March YTD, *not* comparable to a December value |

Because `dim_date` is marked as the date table, `LASTNONBLANK` only sees the dates that survive the year filter, and the tier filter reaches the fact table through `dim_client[client_id]`, so both slicers combine naturally.

**Test query**
```DAX
EVALUATE
VAR LastSnap = CALCULATE ( MAX ( fact_portfolio_snapshot[snapshot_date] ) )
RETURN
UNION (
    ROW ( "slice", "Total", "alpha", [AUM-Weighted Alpha], "last_date", LastSnap,
          "rows_used", CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ),
                                   fact_portfolio_snapshot[snapshot_date] = LastSnap,
                                   fact_portfolio_snapshot[is_return_suspect] = 0 ),
          "with_suspects", CALCULATE ( DIVIDE ( SUMX ( fact_portfolio_snapshot,
                                   fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd] ),
                                   SUM ( fact_portfolio_snapshot[aum] ) ),
                                   fact_portfolio_snapshot[snapshot_date] = LastSnap ) ),
    ROW ( "slice", "2022", "alpha", CALCULATE ( [AUM-Weighted Alpha], dim_date[year] = 2022 ),
          "last_date", CALCULATE ( MAX ( fact_portfolio_snapshot[snapshot_date] ), dim_date[year] = 2022 ),
          "rows_used", BLANK (), "with_suspects", BLANK () ),
    ROW ( "slice", "2024 | UHNW", "alpha", CALCULATE ( [AUM-Weighted Alpha], dim_date[year] = 2024,
                                                       dim_client[client_tier] = "UHNW" ),
          "last_date", BLANK (), "rows_used", BLANK (), "with_suspects", BLANK () ),
    ROW ( "slice", "2024 all months (wrong)", "alpha",
          CALCULATE ( DIVIDE ( SUMX ( fact_portfolio_snapshot,
                      fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd] ),
                      SUM ( fact_portfolio_snapshot[aum] ) ),
                      dim_date[year] = 2024, fact_portfolio_snapshot[is_return_suspect] = 0 ),
          "last_date", BLANK (), "rows_used", BLANK (), "with_suspects", BLANK () )
)
```
What to look for:
1. `last_date` should be the 1st of December of each year (45627 = 2024-12-01 if it shows as a serial number).
2. `rows_used` at the total should equal the clients on the last date minus the suspect rows.
3. `with_suspects` should differ from `alpha`. If it doesn't, the suspect filter isn't doing anything.
4. The "all months" row is a deliberately wrong version. It should be noticeably different (likely lower) than the 2024 value, which shows why the last-date filter matters.
5. Reconcile `alpha` against pandas: on `snapshot_date == max`, `is_return_suspect == 0`, compute `(aum * active_alpha_ytd).sum() / aum.sum()`.

One more edge case: if every row on the last date in some filter were suspect, the measure returns BLANK rather than falling back to an earlier month. I think that is the right behavior for a YTD figure, but it's worth knowing.

---

## Prompt 2 (Debug / Review)

> It ran as written. Test results: Total 0.014480 (last_date 45627, rows_used 2,177, with_suspects 0.016678); 2022 0.028494 (last_date 44896); 2024 | UHNW 0.014097; 2024 all months 0.003225. My pandas reconciliation matches all 9 AUM-Weighted Alpha rows. But my INFO.VIEW.RELATIONSHIPS output shows `dim_date[date]` linked to a `LocalDateTable`, so `dim_date` is **not** actually marked as a date table. Why does the 2024 filter still work, and should I change anything?

## Response 2 (Claude, full)

Good catch, and thanks for checking that against the metadata rather than taking my word for it. You're right: a `LocalDateTable` hanging off `dim_date[date]` means Auto date/time is still active for that column, which only happens when the table is **not** marked as a date table. So my sentence "because `dim_date` is marked as the date table" was wrong for your file.

It doesn't change this measure's result, for two reasons:
1. **`AUM-Weighted Alpha` never removes the year filter.** `LASTNONBLANK` simply iterates the dates already visible after `dim_date[year] = 2024` is applied. Marking the table only matters when a measure *replaces* date filters (time intelligence such as `SAMEPERIODLASTYEAR`), not here.
2. **Your time-intelligence measures are also safe**, because every fact table joins `dim_date` on a **Date-typed** column. When `CALCULATE` filters a date column that is used in a relationship, DAX adds an implicit `REMOVEFILTERS ( dim_date )`, the same behavior a marked date table gets. That's why `Ending AUM LY` for 2024 correctly returns December 2023.

**Recommendation:** no change to the measure. You can mark `dim_date` as the date table (Table tools → Mark as date table → `date`) so the model matches the assignment. If you do, re-run the reconciliation: the numbers should not move.
