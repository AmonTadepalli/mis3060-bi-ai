# HW6: DAX Measure Library (AUM & Performance)
MIS3060 Business Intelligence with AI | Amon Tadepalli

A library of 12 DAX measures on the Wildcat Capital star model, with one report page, reconciled measure by measure to an independent pandas calculation.

## Structure
```
hw06/
├── HW06_DAX_Measure_Library.md      assignment brief
├── powerbi_dax_guide.md             DAX patterns, metadata export, reconciliation (instructor guide)
├── powerbi/
│   ├── hw06.pbix                    instructor model + _Measures table + "Measures" report page
│   ├── measures.md                  Part A documentation and Part C answers
│   ├── dax_01_define_measures.dax   every measure as one DEFINE block (DAX query view → Update model)
│   ├── dax_02_export_values.dax     query that returns powerbi_values.csv (92 rows)
│   └── POWERBI_STEPS.md             click path used in Power BI Desktop
├── scripts/
│   ├── 01_reconcile_measures.py     Part B: pandas recomputation + comparison, exits 1 on any mismatch
│   └── 02_design_questions.py       Part C: pandas evidence for (a)-(d) and the Part D edge case
├── reports/
│   ├── powerbi_values.csv           measure, slice, value (exported from DAX query view)
│   ├── pandas_values.csv            measure, slice, pandas_value
│   ├── measure_reconciliation.csv   measure, slice, powerbi_value, pandas_value, abs_diff, match
│   └── design_questions.txt         output of 02_design_questions.py
├── claude/
│   ├── model_metadata.md            INFO.VIEW columns / relationships / measures
│   ├── dax_session.md               Part D prompt and Claude's full response
│   └── verification.md              Part D verification
└── data/clean/                      the 8 Wildcat Capital Clean CSVs (local only, not committed)
```

## How to run
Put the 8 `Wildcat Capital Clean` CSVs in `hw06/data/clean/`, then from the repo root with the venv active:
```
python hw06/scripts/01_reconcile_measures.py   # ~4 s; writes pandas_values.csv and measure_reconciliation.csv
python hw06/scripts/02_design_questions.py     # ~3 s; writes design_questions.txt
```
`01_reconcile_measures.py` never reads Power BI output to compute its own numbers; it only reads `powerbi_values.csv` for the comparison. Tolerances: 0.01 for currency, 0.0001 for ratios and bps, exact for client counts and the Alpha Signal text. A blank on both sides (for example 2020 YoY) counts as a match.

**Slices covered (92 rows):** all 14 measures at the grand total; measures 0, 1, 4, 6-10 for each year 2020-2024; measures 1-4, 7-11 for each client tier in 2024; measure 5 (plus Ending AUM) for December 2024. `AUM (naive SUM)` is included at the total and by year to show both tools make the same mistake ($566.7B instead of $12.7B).

## Power BI notes
- Started from the posted `Wildcat_Star_Model.pbix` (kept locally, not committed) and saved as `powerbi/hw06.pbix`.
- `dim_date` is **not** marked as a date table in the posted model (the metadata shows an Auto date/time `LocalDateTable` on `dim_date[date]`). Time intelligence still works because every fact joins `dim_date` on a Date column. I left the model as posted; see `claude/verification.md`.
- All measures were added in one step from DAX query view (`dax_01_define_measures.dax` → **Update model**), then formatted in Measure tools.
- `Top 10 Client Share` ranks clients by their balance at the filter's last snapshot date, not by `[Ending AUM]` per client. With `[Ending AUM]`, a client who left would be ranked on an old balance. In this data no departed client would reach the top 10, so both versions give the same numbers; the safer form is kept.

## Reconciliation result
**92 rows, 92 match, 0 mismatch** (`reports/measure_reconciliation.csv`). The largest gap is $0.0001 on the naive SUM total ($566.7B), which comes from Power BI writing numbers to 15 significant digits. Every row matched on the first run, so no side needed fixing.

Two things were checked before trusting the match:
- **Blanks.** 2020 `Ending AUM LY`, `AUM YoY %` and `Organic Growth Rate` are BLANK in Power BI (no 2019) and NaN in pandas. The script counts blank-on-both-sides as a match and any one-sided blank as a mismatch.
- **Both tools make the same mistake.** `AUM (naive SUM)` is $566,681,084,542.48 in both, about 45x the real $12.73B.

## Claude Code review findings
Review of `01_reconcile_measures.py` before committing, run in a Claude agent session (Claude Code harness), including a negative test on a scratch copy of the data.

| Script | What was flagged | What I did |
|---|---|---|
| 01_reconcile_measures.py | Client tiers were a hard-coded list; a new or renamed tier would be silently skipped | Fixed: tiers are read from `dim_client` |
| 01_reconcile_measures.py | `nlargest(10)` drops clients tied at rank 10, but DAX `TOPN` keeps every tie, so the two sides could differ on tied data | Fixed: pandas keeps all clients tied at rank 10. No ties exist today, so the results did not change |
| 01_reconcile_measures.py | `replace("", np.nan)` raised a pandas FutureWarning on every row | Fixed: parse the value with `pd.to_numeric(..., errors="coerce")` and treat "" as BLANK |
| 01_reconcile_measures.py | A grid pasted straight from DAX query view is tab-separated with `[measure]` headers; `read_csv` would read it as one column | Fixed: delimiter is sniffed and brackets are stripped from the headers |
| 01_reconcile_measures.py | Negative test: changed one Power BI value and nudged every Ending AUM by $0.004 in a scratch copy | No change needed: the changed value failed, the $0.004 nudges passed (inside the 0.01 tolerance), and the script exited 1 |
| 01_reconcile_measures.py | A row present in only one file could be missed | Kept: the outer merge already marks it `match = False` and prints it |
