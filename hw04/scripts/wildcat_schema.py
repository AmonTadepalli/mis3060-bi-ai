"""
Shared schema for the Wildcat Capital extract (HW4).

This file holds the *expectations* (types, keys, allowed values, ranges,
foreign keys). The profiling, cleaning and validation scripts are generic:
they read these rules instead of hard-coding them per table.

Types used:
  int      whole number written without a decimal point (e.g. 45, not 45.0)
  float    any number
  date     ISO date YYYY-MM-DD
  bool     the text True / False
  flag01   the text 0 / 1
  text     free text
"""
from pathlib import Path

HW_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = HW_DIR / "data" / "raw"
CLEAN_DIR = HW_DIR / "data" / "clean"
AUDIT_DIR = HW_DIR / "data" / "audit"
REPORTS_DIR = HW_DIR / "reports"

TABLES = [
    "dim_advisor", "dim_benchmark", "dim_client", "dim_date", "dim_security",
    "fact_fees", "fact_portfolio_snapshot", "fact_transactions",
]

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
    "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}

# Each column: type, plus optional allowed / min / max / pattern / nullable.
# nullable=True means a blank is a legitimate value for that column.
SCHEMA = {
    "dim_advisor": {
        "pk": "advisor_id",
        "columns": {
            "advisor_id": {"type": "int", "min": 1},
            "first_name": {"type": "text"},
            "last_name": {"type": "text"},
            "region": {"type": "text", "allowed": ["Northeast", "Mid-Atlantic", "Southeast", "Midwest", "West"]},
            "years_experience": {"type": "int", "min": 0, "max": 50},
            "aum_target_mm": {"type": "int", "min": 1},
            # "None" is a real answer here (no certification), not a missing value
            "certifications": {"type": "text", "allowed": ["None", "CFA", "CFP", "CFP, CFA", "CFP, CIMA", "CIMA", "CFA, CIMA"]},
        },
    },
    "dim_benchmark": {
        "pk": "benchmark_id",
        "columns": {
            "benchmark_id": {"type": "int", "min": 1},
            "name": {"type": "text"},
            "asset_class": {"type": "text"},
            "ticker_proxy": {"type": "text"},
        },
    },
    "dim_client": {
        "pk": "client_id",
        "columns": {
            "client_id": {"type": "int", "min": 1},
            "first_name": {"type": "text"},
            "last_name": {"type": "text"},
            "age": {"type": "int", "min": 18, "max": 110},
            "city": {"type": "text"},
            "state": {"type": "text", "allowed": sorted(US_STATES)},
            "zip_code": {"type": "text", "pattern": r"^\d{5}$"},
            "risk_profile": {"type": "text", "allowed": ["Conservative", "Moderately Conservative", "Balanced",
                                                          "Moderately Aggressive", "Aggressive"]},
            "client_tier": {"type": "text", "allowed": ["Retail", "HNW", "UHNW"]},
            "primary_account_type": {"type": "text", "allowed": ["Taxable", "IRA", "Roth IRA", "Trust", "529"]},
            "initial_aum": {"type": "float", "min": 0.01},
            "client_since": {"type": "date", "min": "2000-01-01", "max": "2024-12-31"},
            "advisor_id": {"type": "int", "min": 1},
            "is_active": {"type": "bool"},
        },
        # Two clients are "the same person" if everything except id and last name matches
        "near_dup_cols": ["first_name", "age", "city", "state", "zip_code", "risk_profile", "client_tier",
                          "primary_account_type", "initial_aum", "client_since", "advisor_id", "is_active"],
    },
    "dim_date": {
        "pk": "date_id",
        "columns": {
            "date_id": {"type": "int", "min": 1},
            "date": {"type": "date", "min": "2020-01-01", "max": "2024-12-31"},
            "year": {"type": "int", "min": 2020, "max": 2024},
            "quarter": {"type": "int", "min": 1, "max": 4},
            "month": {"type": "int", "min": 1, "max": 12},
            "month_name": {"type": "text", "allowed": ["January", "February", "March", "April", "May", "June", "July",
                                                        "August", "September", "October", "November", "December"]},
            "week_of_year": {"type": "int", "min": 1, "max": 53},
            "day_of_week": {"type": "text", "allowed": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                                                         "Saturday", "Sunday"]},
            "is_month_end": {"type": "flag01"},
            "is_quarter_end": {"type": "flag01"},
            "is_year_end": {"type": "flag01"},
            "is_trading_day": {"type": "flag01"},
        },
        "unique": ["date"],
    },
    "dim_security": {
        "pk": "security_id",
        "columns": {
            "security_id": {"type": "int", "min": 1},
            "ticker": {"type": "text", "pattern": r"^[A-Z]{1,5}$"},
            "name": {"type": "text"},
            "asset_class": {"type": "text", "allowed": ["Equity", "Fixed Income", "Alternative", "Cash Equivalent"]},
            # blank sector is legitimate for ETFs (checked in single-table rules)
            "sector": {"type": "text", "nullable": True},
            "benchmark_id": {"type": "int", "min": 1},
            "is_etf": {"type": "bool"},
            # blank expense ratio is legitimate for single stocks
            "expense_ratio_bps": {"type": "float", "min": 0, "max": 300, "nullable": True},
        },
        "unique": ["ticker"],
    },
    "fact_fees": {
        "pk": "fee_id",
        "columns": {
            "fee_id": {"type": "int", "min": 1},
            "client_id": {"type": "int", "min": 1},
            "advisor_id": {"type": "int", "min": 1},
            "fee_date": {"type": "date", "min": "2020-01-01", "max": "2024-12-31"},
            "fee_type": {"type": "text", "allowed": ["Management", "Advisory", "Custodial", "Performance"]},
            "aum_basis": {"type": "float", "min": 0.01},
            "bps_charged": {"type": "float", "min": 0, "max": 300},
            "amount": {"type": "float", "min": 0.01},
        },
        "grain": ["client_id", "fee_date"],
    },
    "fact_portfolio_snapshot": {
        "pk": "snapshot_id",
        "columns": {
            "snapshot_id": {"type": "int", "min": 1},
            "client_id": {"type": "int", "min": 1},
            "advisor_id": {"type": "int", "min": 1},
            "benchmark_id": {"type": "int", "min": 1},
            "snapshot_date": {"type": "date", "min": "2020-01-01", "max": "2024-12-31"},
            "year": {"type": "int", "min": 2020, "max": 2024},
            "month": {"type": "int", "min": 1, "max": 12},
            "aum": {"type": "float", "min": 0.01},
            "return_ytd": {"type": "float", "min": -1.0},
            "benchmark_return_ytd": {"type": "float", "min": -1.0},
            "active_alpha_ytd": {"type": "float"},
            "cash_pct": {"type": "float", "min": 0, "max": 1},
            "account_type": {"type": "text", "allowed": ["Taxable", "IRA", "Roth IRA", "Trust", "529"]},
        },
        "grain": ["client_id", "snapshot_date"],
    },
    "fact_transactions": {
        "pk": "txn_id",
        "columns": {
            "txn_id": {"type": "int", "min": 1},
            "client_id": {"type": "int", "min": 1},
            "advisor_id": {"type": "int", "min": 1},
            # blank for cash movements (Deposit / Withdrawal / Advisory Fee): checked by txn_type rule
            "security_id": {"type": "int", "min": 1, "nullable": True},
            "txn_date": {"type": "date", "min": "2020-01-01", "max": "2024-12-31"},
            "txn_type": {"type": "text", "allowed": ["Buy", "Sell", "Dividend", "Deposit", "Withdrawal", "Advisory Fee"]},
            "shares": {"type": "float", "min": 0, "nullable": True},
            "price": {"type": "float", "min": 0.01, "nullable": True},
            "amount": {"type": "float", "min": 0.01},
        },
    },
}

# Foreign keys: (fact_table, fact_column, dim_table, dim_column)
# Ten ID-based relationships, then three that join to the date table.
RELATIONSHIPS = [
    ("dim_client", "advisor_id", "dim_advisor", "advisor_id"),
    ("dim_security", "benchmark_id", "dim_benchmark", "benchmark_id"),
    ("fact_fees", "client_id", "dim_client", "client_id"),
    ("fact_fees", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_portfolio_snapshot", "client_id", "dim_client", "client_id"),
    ("fact_portfolio_snapshot", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_portfolio_snapshot", "benchmark_id", "dim_benchmark", "benchmark_id"),
    ("fact_transactions", "client_id", "dim_client", "client_id"),
    ("fact_transactions", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_transactions", "security_id", "dim_security", "security_id"),
    ("fact_fees", "fee_date", "dim_date", "date"),
    ("fact_portfolio_snapshot", "snapshot_date", "dim_date", "date"),
    ("fact_transactions", "txn_date", "dim_date", "date"),
]

# Cash movements carry no security, shares or price
CASH_TXN_TYPES = ["Deposit", "Withdrawal", "Advisory Fee"]
SECURITY_TXN_TYPES = ["Buy", "Sell", "Dividend"]


def load_tables(folder):
    """Read every table as text so nothing is silently converted."""
    import pandas as pd
    return {t: pd.read_csv(Path(folder) / f"{t}.csv", dtype=str, keep_default_na=False) for t in TABLES}
