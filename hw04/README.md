# HW4: Cleaning the Wildcat Capital Data
MIS3060 Business Intelligence with AI | Amon Tadepalli

## Structure
```
hw04/
├── HW04_Data_Cleaning.md      assignment brief
├── decision_log.md            Part B: one entry per issue, written before cleaning code
├── scripts/
│   ├── 01_profile.py          Part A: generic profiler + DQ checks
│   ├── 02_clean.py            Part C: raw -> clean, asserted, audited
│   └── 03_validate.py         Part D: RI function, rules, reconciliations, scorecard
├── data/
│   ├── raw/                   8 source CSVs (local only, not committed, never modified)
│   ├── clean/                 8 clean CSVs + README_clean.md
│   └── audit/                 cleaning_log.csv, value_changes.csv, quarantine_*.csv
└── reports/
    ├── profile_raw.csv
    ├── dq_summary_raw.csv
    ├── data_quality_scorecard.csv
    └── cleaning_report.md     Part E
```

## How to run
From the repo root, with the venv active:
```
python hw04/scripts/01_profile.py
python hw04/scripts/02_clean.py
python hw04/scripts/03_validate.py
```

## Claude Code review findings
| Script | What Claude Code flagged | What I did |
|---|---|---|
| 01_profile.py | | |
| 02_clean.py | | |
| 03_validate.py | | |
