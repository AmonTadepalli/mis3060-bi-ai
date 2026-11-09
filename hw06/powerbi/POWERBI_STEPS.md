# HW6 Power BI steps (about 30 minutes)

Everything below happens in Power BI Desktop. The DAX is already written in two files in this folder, so there is nothing to type by hand.

## 1. Open and save the model
1. Open `hw06/powerbi/Wildcat_Star_Model.pbix` (the instructor model).
2. **File → Save as** `hw06/powerbi/hw06.pbix`.
3. **Home → Enter data**, name the table `_Measures`, click **Load**.

## 2. Add all measures at once
1. Open **DAX query view** (left rail, the `{}` icon), new query tab.
2. Paste the whole of `dax_01_define_measures.dax`, click **Run**. The result is one row: Ending AUM should be **12,729,572,078.86**, Ending Clients **2,325**.
3. Above `DEFINE`, click **Update model: Add 16 new measures** (if it says "overwrite" for Total Fees / Net Flows, that is fine).
4. In the Data pane, delete `Column1` from `_Measures`.

## 3. Format the measures
Select each measure in the Data pane, then set the format in **Measure tools**:

| Measures | Format |
|---|---|
| AUM (naive SUM), Ending AUM, Avg AUM per Client, Ending AUM LY, Ending AUM PM, Avg Monthly AUM, Total Fees, Net Flows | Currency, 2 decimals |
| Ending Clients | Whole number, thousands separator |
| AUM YoY %, AUM MoM %, Organic Growth Rate, AUM-Weighted Alpha, Top 10 Client Share | Percentage, 2 decimals |
| Fee Yield (bps) | Decimal number, 2 decimals |

In the Description box of `AUM (naive SUM)`, type: *WRONG ON PURPOSE: sums a balance across months. Do not use on reports.*

## 4. Build the Measures report page
1. Report view, rename the page **Measures**.
2. Four **Card** visuals: Ending AUM, Ending Clients, Avg AUM per Client, Top 10 Client Share.
3. **Table** visual: `dim_date[year]`, Ending AUM, AUM YoY %, Avg Monthly AUM, Fee Yield (bps), Organic Growth Rate, AUM-Weighted Alpha, Alpha Signal.
4. **Table** visual: `dim_client[client_tier]`, Ending AUM, Avg AUM per Client, AUM YoY %, Fee Yield (bps), Organic Growth Rate, AUM-Weighted Alpha, Alpha Signal, Top 10 Client Share. Then, with this table selected: **Filters** pane → *Filters on this visual* → drag `dim_date[year]` in → tick **2024**.
5. Save with the Measures page open.

Quick check: 2024 row of the year table should read Ending AUM $12,729,572,078.86, YoY 19.58%, Fee Yield 43.15, Alpha 1.45%, "In line".

## 5. Export the numbers (Part B)
1. DAX query view, new tab, paste `dax_02_export_values.dax`, **Run** (92 rows).
2. **Copy** the result grid (with headers) and paste it into `hw06/reports/powerbi_values.csv`. Tab-separated is fine; the script detects it.

## 6. Export metadata (Part D)
In DAX query view, run each of the three queries below in its own tab and copy each grid. Paste all three into chat (or into `hw06/claude/model_metadata.md`).
```DAX
EVALUATE
SELECTCOLUMNS (
    FILTER ( INFO.VIEW.COLUMNS (), [DataCategory] <> "RowNumber" ),
    [Table], "Column", [Name], [DataType], "DAX formula", [Expression], [IsHidden]
)
ORDER BY [Table]
```
```DAX
EVALUATE INFO.VIEW.RELATIONSHIPS ()
```
```DAX
EVALUATE
SELECTCOLUMNS (
    INFO.VIEW.MEASURES (),
    [Table], "Measure", [Name], "DAX formula", [Expression], [FormatString], [State]
)
```

## 7. Part D test query
Run this and note the result for `claude/verification.md`:
```DAX
EVALUATE
VAR LastSnap = CALCULATE ( MAX ( fact_portfolio_snapshot[snapshot_date] ) )
RETURN
UNION (
    ROW ( "slice", "Total", "alpha", [AUM-Weighted Alpha], "rows", CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ), fact_portfolio_snapshot[snapshot_date] = LastSnap, fact_portfolio_snapshot[is_return_suspect] = 0 ) ),
    ROW ( "slice", "2022", "alpha", CALCULATE ( [AUM-Weighted Alpha], dim_date[year] = 2022 ), "rows", BLANK () ),
    ROW ( "slice", "2024 | UHNW", "alpha", CALCULATE ( [AUM-Weighted Alpha], dim_date[year] = 2024, dim_client[client_tier] = "UHNW" ), "rows", BLANK () )
)
```
Expected: Total 0.01448 with 2,177 rows; 2022 0.02849; 2024 | UHNW 0.01410.
