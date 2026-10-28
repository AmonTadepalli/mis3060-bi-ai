"""
HW5 Parts A and B: prove the keys and grain of the Wildcat Capital star schema.

Checks, all on the 8 instructor-released clean CSVs in hw05/data/clean/:
  1. Row and column counts match the handout
  2. Primary keys are unique and never blank
  3. Every foreign key matches its parent column (blank allowed only where stated)
  4. Fact dates join to dim_date[date], not dim_date[date_id]
  5. Grain: each fact's "one row represents" key combination is unique
  6. Structure behind the Part E answers: blank security_id only on cash rows,
     fact advisor_id always equals the client's advisor in dim_client

Tables are read with dtype=str and keep_default_na=False so keys are compared
exactly as stored (a "45.0" would not silently match "45"), and so the text
"None" in dim_advisor[certifications] is not mistaken for a blank.

Writes hw05/reports/key_checks.csv (result = PASS / FAIL / INFO). Exits with code 1 if any check fails.

Run from the repo root:  python hw05/scripts/01_keys_grain.py
"""
import sys
from pathlib import Path

import pandas as pd

HW = Path(__file__).resolve().parent.parent
DATA = HW / "data" / "clean"
REPORTS = HW / "reports"

# Handout row and column counts
EXPECTED = {
    "dim_advisor": (25, 7),
    "dim_benchmark": (8, 4),
    "dim_client": (2_500, 14),
    "dim_date": (1_827, 12),
    "dim_security": (500, 8),
    "fact_fees": (122_197, 8),
    "fact_portfolio_snapshot": (129_547, 14),
    "fact_transactions": (298_572, 10),
}

PRIMARY_KEYS = {
    "dim_advisor": "advisor_id",
    "dim_benchmark": "benchmark_id",
    "dim_client": "client_id",
    "dim_date": "date_id",
    "dim_security": "security_id",
    "fact_fees": "fee_id",
    "fact_portfolio_snapshot": "snapshot_id",
    "fact_transactions": "txn_id",
}

# (child table, child column, parent table, parent column, blank allowed?)
FOREIGN_KEYS = [
    ("dim_client", "advisor_id", "dim_advisor", "advisor_id", False),
    ("dim_security", "benchmark_id", "dim_benchmark", "benchmark_id", False),
    ("fact_fees", "client_id", "dim_client", "client_id", False),
    ("fact_fees", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_fees", "fee_date", "dim_date", "date", False),
    ("fact_portfolio_snapshot", "client_id", "dim_client", "client_id", False),
    ("fact_portfolio_snapshot", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_portfolio_snapshot", "benchmark_id", "dim_benchmark", "benchmark_id", False),
    ("fact_portfolio_snapshot", "snapshot_date", "dim_date", "date", False),
    ("fact_transactions", "client_id", "dim_client", "client_id", False),
    ("fact_transactions", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_transactions", "security_id", "dim_security", "security_id", True),
    ("fact_transactions", "txn_date", "dim_date", "date", False),
]

# Candidate grain for each fact: the columns that should make a row unique
GRAIN = {
    "fact_fees": ["client_id", "fee_date"],
    "fact_portfolio_snapshot": ["client_id", "snapshot_date"],
    "fact_transactions": ["txn_id"],
}

CASH_TYPES = {"Deposit", "Withdrawal", "Advisory Fee"}

results = []


def record(check, table, column, detail, passed, value="", info=False):
    """passed=True/False gives PASS/FAIL; info=True records a count that is not a test."""
    results.append({
        "check": check, "table": table, "column": column, "detail": detail, "value": value,
        "result": "INFO" if info else ("PASS" if passed else "FAIL"),
    })


def load():
    tables = {}
    for name in EXPECTED:
        path = DATA / f"{name}.csv"
        if not path.exists():
            sys.exit(f"Missing {path}. Put the 8 clean CSVs in hw05/data/clean/.")
        tables[name] = pd.read_csv(path, dtype=str, keep_default_na=False)
    return tables


def check_counts(t):
    for name, (rows, cols) in EXPECTED.items():
        got = t[name].shape
        record("row_count", name, "", f"expected {rows:,} x {cols}", got == (rows, cols),
               f"{got[0]:,} x {got[1]}")


def check_primary_keys(t):
    for name, pk in PRIMARY_KEYS.items():
        col = t[name][pk]
        blanks = (col == "").sum()
        dups = col.duplicated().sum()
        record("pk_not_blank", name, pk, "no blank primary keys", blanks == 0, blanks)
        record("pk_unique", name, pk, "no duplicate primary keys", dups == 0, dups)


def check_foreign_keys(t):
    for child, ccol, parent, pcol, blank_ok in FOREIGN_KEYS:
        values = t[child][ccol]
        parent_values = set(t[parent][pcol])
        blank = values == ""
        orphans = (~blank & ~values.isin(parent_values)).sum()
        label = f"{ccol} -> {parent}[{pcol}]"
        record("fk_integrity", child, ccol, label, orphans == 0, orphans)
        if blank_ok:
            record("fk_blank", child, ccol, "blanks allowed (counted, not tested)", True, blank.sum(), info=True)
        else:
            record("fk_blank", child, ccol, "no blanks allowed", blank.sum() == 0, blank.sum())

    # The parent side of a date join must itself be unique, or the relationship is many-to-many
    dups = t["dim_date"]["date"].duplicated().sum()
    record("join_column_unique", "dim_date", "date", "date is unique, so it can be the one side", dups == 0, dups)

    # Show why date_id is the wrong join column: the fact dates never match it.
    # (Illustrative: a date string can never equal an integer id, so this documents the
    # Part E (c) answer rather than testing for a defect that could plausibly occur.)
    date_ids = set(t["dim_date"]["date_id"])
    for child, col in [("fact_fees", "fee_date"), ("fact_portfolio_snapshot", "snapshot_date"),
                       ("fact_transactions", "txn_date")]:
        matches = t[child][col].isin(date_ids).sum()
        record("date_id_mismatch", child, col, "fact dates match dim_date[date_id] (expect 0)",
               matches == 0, matches)


def check_grain(t):
    for name, cols in GRAIN.items():
        dups = t[name].duplicated(cols).sum()
        record("grain_unique", name, ", ".join(cols), "one row per grain key", dups == 0, dups)

    # Monthly facts: every date parses and is the first of the month
    for name, col in [("fact_fees", "fee_date"), ("fact_portfolio_snapshot", "snapshot_date")]:
        parsed = pd.to_datetime(t[name][col], format="%Y-%m-%d", errors="coerce")
        not_first = (parsed.isna() | (parsed.dt.day != 1)).sum()
        record("monthly_date", name, col, "every date is the 1st of a month", not_first == 0, not_first)

    # Transactions have no natural key: show that the obvious combination repeats
    natural = ["client_id", "txn_date", "security_id", "txn_type"]
    dups = t["fact_transactions"].duplicated(natural).sum()
    record("no_natural_key", "fact_transactions", ", ".join(natural),
           "repeats exist, so txn_id is the only grain key", True, dups, info=True)


def check_structure(t):
    tx = t["fact_transactions"]
    blank = tx["security_id"] == ""
    blank_non_cash = (blank & ~tx["txn_type"].isin(CASH_TYPES)).sum()
    filled_cash = (~blank & tx["txn_type"].isin(CASH_TYPES)).sum()
    record("blank_security_cash_only", "fact_transactions", "security_id",
           "blank only on Deposit / Withdrawal / Advisory Fee", blank_non_cash == 0, blank_non_cash)
    record("cash_rows_have_no_security", "fact_transactions", "security_id",
           "cash rows never carry a security", filled_cash == 0, filled_cash)

    # advisor_id on each fact agrees with dim_client, so dim_client -> dim_advisor is a redundant path
    client_adv = t["dim_client"].set_index("client_id")["advisor_id"]
    for name in GRAIN:
        f = t[name]
        # Compare only rows whose client exists; orphan clients are already failed by fk_integrity
        known = f["client_id"].map(client_adv)
        mismatch = (known.notna() & (f["advisor_id"] != known)).sum()
        record("advisor_matches_client", name, "advisor_id",
               "fact advisor_id equals the client's advisor in dim_client", mismatch == 0, mismatch)


def main():
    t = load()
    check_counts(t)
    check_primary_keys(t)
    check_foreign_keys(t)
    check_grain(t)
    check_structure(t)

    report = pd.DataFrame(results)
    REPORTS.mkdir(exist_ok=True)
    report.to_csv(REPORTS / "key_checks.csv", index=False)

    pd.set_option("display.width", 200, "display.max_colwidth", 60, "display.max_rows", 200)
    print(report[["check", "table", "column", "value", "result"]].to_string(index=False))
    counts = report["result"].value_counts()
    failed = counts.get("FAIL", 0)
    print(f"\n{counts.get('PASS', 0)} passed, {failed} failed, {counts.get('INFO', 0)} info rows. "
          f"Report: {REPORTS / 'key_checks.csv'}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
