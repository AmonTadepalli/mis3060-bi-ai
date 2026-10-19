# HW4: Cleaning the Wildcat Capital Data
MIS3060 Business Intelligence with AI | Amon Tadepalli

Audit, clean and validate the 8-table Wildcat Capital extract. Result: 555,401 raw rows become 555,176 clean rows plus 225 quarantined (none deleted), and all 13 relationships join at 100%.

## Structure
```
hw04/
├── HW04_Data_Cleaning.md      assignment brief
├── decision_log.md            Part B: 21 issues, written before cleaning code
├── scripts/
│   ├── wildcat_schema.py      shared rules: types, keys, allowed values, ranges, 13 relationships
│   ├── 01_profile.py          Part A: generic profiler + 4 groups of checks
│   ├── 02_clean.py            Part C: 9 asserted steps, quarantine, audit trail
│   └── 03_validate.py         Part D: check_referential_integrity(), rules, reconciliations, IQR, scorecard
├── data/
│   ├── raw/                   8 source CSVs (local only, not committed, never modified)
│   ├── clean/                 8 clean CSVs + README_clean.md
│   └── audit/                 cleaning_log.csv, value_changes.csv, 2 quarantine files
└── reports/
    ├── profile_raw.csv            per-column profile of raw data
    ├── dq_summary_raw.csv         every check, tagged ERROR / WARN / INFO / PASS
    ├── data_quality_scorecard.csv one row per table per stage
    ├── ri_results.csv             13 relationships, raw and clean
    ├── rule_results.csv           every rule, raw and clean
    ├── reconciliations.csv        8 reconciliations, raw and clean
    ├── outliers_iqr.csv           IQR fences and flagged counts
    └── cleaning_report.md         Part E: memo to the portfolio committee
```

## How to run
Put the 8 Wildcat Capital CSVs in `hw04/data/raw/`, then from the repo root with the venv active:
```
python hw04/scripts/01_profile.py     # about 40 s, writes reports/profile_raw.csv + dq_summary_raw.csv
python hw04/scripts/02_clean.py       # writes data/clean/ and data/audit/; stops on any failed assert
python hw04/scripts/03_validate.py    # writes the scorecard and the other Part D reports
```
`01_profile.py some_file.csv` profiles any single CSV, showing the profiler is not tied to these tables.

## Claude Code review findings
| Script | What Claude Code flagged | What I did |
|---|---|---|
| 01_profile.py | Running-position check sorted same-day trades by txn_id as text, so "10" came before "9" | Fixed: sort on numeric txn_id. Re-ran; count unchanged (43,010) |
| 01_profile.py | RI "after normalisation" cast keys to int64, which would silently turn a bad key like 45.5 into 45 | Fixed: only exact `N` or `N.0` keys are normalised; anything else stays an orphan |
| 01_profile.py | Benchmark-to-risk mapping (Aggressive -> 1, Balanced -> 3, Conservative -> 8) is inferred from the data, not from a documented source | Kept: it passes on 100% of rows with a profile; noted here as an assumption |
| 02_clean.py | Same text sort in `oversold_sells()` | Fixed with numeric sort. Re-ran; D16 count unchanged (42,975) |
| 02_clean.py | State-name map is hard-coded to the 7 names seen in the audit | Kept on purpose: an `assert` stops the script if a new unmapped name appears, rather than guessing |
| 03_validate.py | Scorecard mixed text ("n/a") into a numeric column, which would make a BI tool read it as text | Fixed: tables with no foreign keys now show a blank referential match |
| 03_validate.py | `check_referential_integrity()` compares keys as text, so it gives false orphans if Assignment 5 reads files with default types | Kept (that strictness is what caught the 45.0 defect) and documented in the docstring: read both tables with `dtype=str` |
