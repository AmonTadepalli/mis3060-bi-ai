# Part D verification: AUM-Weighted Alpha (measure 9)

## Did it run as written?
Yes. Claude's measure was added to `_Measures` unchanged and its State is **Valid** in `INFO.VIEW.MEASURES`. Claude's test query ran on the first try:

| slice | alpha | last_date | rows_used | with_suspects |
|---|---:|---|---:|---:|
| Total | 0.014480 | 45627 (2024-12-01) | 2,177 | 0.016678 |
| 2022 | 0.028494 | 44896 (2022-12-01) | | |
| 2024 \| UHNW | 0.014097 | | | |
| 2024 all months (wrong) | 0.003225 | | | |

## Which reconciliation rows prove it
In `reports/measure_reconciliation.csv`, all 9 `AUM-Weighted Alpha` rows match pandas within 0.0001 (largest gap below 1e-12): `Total`, `2020` to `2024`, and `2024 | Retail`, `2024 | HNW`, `2024 | UHNW`. The pandas side (`weighted_alpha()` in `01_reconcile_measures.py`) never reads Power BI. It takes the last `snapshot_date` in the slice, drops `is_return_suspect = 1`, and computes `Σ(aum × alpha) / Σ aum`. The 9 `Alpha Signal` rows, which depend on this measure, also match.

## Edge cases checked
1. **Grand total.** Last date 2024-12-01, 2,177 rows used = 2,325 clients − 148 suspect rows (pandas: `design_questions.txt` (c)). Matches pandas 0.014480.
2. **`dim_date[year]` = 2022.** `last_date` is 2022-12-01, so the measure reads the full-year 2022 alpha, not 2024's. Value 2.85% ("Outperforming"), equal to pandas.
3. **2024 tier table (visual filter).** UHNW 1.41%, HNW 1.40%, Retail 2.40%. All three match pandas. On the report page, the visual-level 2024 filter gives the same numbers as `CALCULATE(..., dim_date[year] = 2024, dim_client[client_tier] = ...)`.
4. **Suspects really are removed.** With suspects included, the weight is 1.668% vs 1.448%, in both DAX (`with_suspects`) and pandas.
5. **Last-date logic matters.** Weighting every 2024 month gives 0.32%, a fifth of the correct value. That confirms Claude's warning about mixing YTD windows.
6. **2020 (first year).** No prior data is needed, so 2020 returns a value (−0.68%), not blank. It matches pandas.

## What I changed and why
Nothing in the measure. It matched pandas in every slice tested, it handles blanks with `DIVIDE`, and it finds the last date before applying the suspect filter. That is the right order: a month counts as "last" if it has any data, consistent with `[Ending AUM]`.

The only change was to my own understanding of the model (see below). I did not mark `dim_date` as a date table, so that the file matches the posted starting model. Marking it would not change any number.

## One claim confirmed and one refuted
- **Refuted:** Claude said the slicers combine correctly "because `dim_date` is marked as the date table". The relationships export shows `dim_date[date] → LocalDateTable_30b0d5f8`, which only exists when Auto date/time is on, so `dim_date` is **not** marked. When challenged (Prompt 2), Claude corrected itself: this measure never removes date filters, and time intelligence elsewhere works because the relationships use Date-typed columns. I confirmed that in the reconciliation: `Ending AUM LY` for 2024 returns $10,644,971,737.00, the December 2023 balance.
- **Confirmed:** Claude predicted the all-months version would be "noticeably different (likely lower)". It is: 0.32% vs 1.45% in Power BI, and 0.3225% in pandas.
