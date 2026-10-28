# HW5: Modeling the Wildcat Capital Data as a Star Schema in Power BI
MIS3060 Business Intelligence with AI | Amon Tadepalli

Identify the keys, grain and measure types of the 8 clean Wildcat Capital tables, then build the star schema in Power BI. No new tables or columns: the clean files are loaded as they are.

## Structure
```
hw05/
├── HW05_Star_Schema_and_Power_BI.md   assignment brief
├── powerbi_guide.md                   Power BI mechanics (Part D)
├── star_design.md                     Parts A, B, C, E, F
├── scripts/
│   └── 01_keys_grain.py               Parts A/B: PK uniqueness, FK integrity, date join, grain (63 checks + 2 info rows)
├── reports/
│   └── key_checks.csv                 one row per check, PASS / FAIL / INFO
├── data/
│   └── clean/                         8 instructor-released clean CSVs (local only, not committed)
└── powerbi/
    ├── hw05.pbix                      saved model
    └── model_view.png                 full Model view screenshot
```

## How to run
Put the 8 `Wildcat Capital Clean` CSVs in `hw05/data/clean/`, then from the repo root with the venv active:
```
python hw05/scripts/01_keys_grain.py   # a few seconds; writes reports/key_checks.csv, exits 1 on any FAIL
```

## Power BI model notes
- `powerbi/hw05.pbix` is 21 MB, so it is committed here (under GitHub's 100 MB limit).
- Types are set in Power Query: keys Whole Number, the five date columns Date, amounts and rates Decimal, `zip_code` / `account_type` / `primary_account_type` Text, `is_active` True/False, the 0/1 `is_*` flags Whole Number.
- One deviation from the guide: `dim_security[is_etf]` is stored as the text `True`/`False`, which cannot convert to Whole Number, so it is loaded as True/False like `is_active`.
- Auto-detected relationships were deleted (they made `dim_client → dim_advisor` active and the fact → `dim_client` links inactive) and the 13 designed relationships were built by hand. The only DAX is one `COUNTROWS` measure per table; all eight match the handout row counts.

## Claude Code review findings
| Script | What Claude Code flagged | What I did |
|---|---|---|
| 01_keys_grain.py | Negative test: planted an orphan `client_id`, a `45.0` security key, a duplicate `txn_id`, a blank `security_id` on a Buy and a mid-month `fee_date` in a scratch copy of the data | No change needed: every defect was caught and the script exited with code 1. The `45.0` key fails as an orphan on purpose (keys are compared as stored text, the same strictness that caught the HW4 defect) |
| 01_keys_grain.py | Two rows always reported PASS without testing anything (the count of allowed blank `security_id` and the 622 natural-key repeats), inflating the pass count | Fixed: added an INFO result for counts that are not tests. Re-ran: 63 PASS, 0 FAIL, 2 INFO |
| 01_keys_grain.py | Month-start check used `str.endswith("-01")`, which checks text, not dates, and would pass a malformed value | Fixed: parse with `pd.to_datetime(format="%Y-%m-%d")` and fail anything unparseable or not on day 1. Result unchanged (0) |
| 01_keys_grain.py | An orphan `client_id` was reported twice: as an orphan and again as an advisor mismatch (the lookup returned NaN) | Fixed: the advisor check compares only rows whose client exists. Negative test now reports 7 distinct failures instead of 8 |
| 01_keys_grain.py | `date_id_mismatch` can never fail, because a date string cannot equal an integer id | Kept: it documents the Part E (c) answer rather than testing for a likely defect; noted in a code comment |
| 01_keys_grain.py | Expected row counts are hard-coded from the handout | Kept on purpose: the script should fail if the released files ever change |
