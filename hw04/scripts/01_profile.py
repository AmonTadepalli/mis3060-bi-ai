"""
HW4 Part A: audit the raw Wildcat Capital extract.

1. profile_table() works on ANY DataFrame read as text: no column names are
   hard-coded. If a schema is supplied it also measures parse failures against
   the expected type; without one it infers the type from the data.
2. Four groups of checks, each finding tagged ERROR / WARN / INFO:
     1 column level        type, allowed values, ranges, key uniqueness
     2 single-table rules  duplicates, near-duplicates, row contradictions
     3 referential         every FK points at an existing PK
     4 cross-table         facts that disagree with dimensions or each other

Outputs: reports/profile_raw.csv, reports/dq_summary_raw.csv

Usage:  python hw04/scripts/01_profile.py            (profiles data/raw)
        python hw04/scripts/01_profile.py some.csv    (profiles any single CSV)
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wildcat_schema import (CASH_TXN_TYPES, RAW_DIR, RELATIONSHIPS, REPORTS_DIR, SCHEMA,
                            SECURITY_TXN_TYPES, load_tables)

# --------------------------------------------------------------------------
# Generic parsing helpers
# --------------------------------------------------------------------------
INT_RE = re.compile(r"^-?\d+$")
FLOAT_RE = re.compile(r"^-?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def value_shape(v):
    """Reduce a value to its pattern: digits -> 9, runs of letters -> A."""
    return re.sub(r"[A-Za-z]+", "A", re.sub(r"\d", "9", v))


def parses_as(s, typ):
    """Boolean Series: does each non-blank value parse as the type?"""
    if typ == "int":
        return s.str.match(INT_RE)
    if typ == "float":
        return s.str.match(FLOAT_RE)
    if typ == "date":
        ok = s.str.match(DATE_RE)
        return ok & pd.to_datetime(s.where(ok), format="%Y-%m-%d", errors="coerce").notna()
    if typ == "bool":
        return s.isin(["True", "False"])
    if typ == "flag01":
        return s.isin(["0", "1"])
    return pd.Series(True, index=s.index)


def infer_type(s):
    """Guess a column's type when no schema is given (>=95% of values parse)."""
    v = s[s.str.strip() != ""]
    if v.empty:
        return "text"
    for typ in ["flag01", "bool", "int", "float", "date"]:
        if parses_as(v, typ).mean() >= 0.95:
            return typ
    return "text"


def to_num(s):
    return pd.to_numeric(s.where(s.str.strip() != ""), errors="coerce")


# --------------------------------------------------------------------------
# Generic column profile (works on any table)
# --------------------------------------------------------------------------
def profile_table(df, table, schema=None):
    rows = []
    for col in df.columns:
        s = df[col].astype(str)
        spec = (schema or {}).get("columns", {}).get(col, {})
        typ = spec.get("type") or infer_type(s)
        blank = s.str.strip() == ""
        null_words = s.str.strip().str.lower().isin(["none", "null", "nan", "n/a", "na", "-"])
        nonblank = s[~blank]
        shapes = nonblank.map(value_shape).value_counts()
        top = "; ".join(f"{k} ({v / max(len(nonblank), 1):.1%})" for k, v in shapes.head(3).items())
        # a "mixed format" = more than one structural format (digit runs collapsed, so 99.9 == 999.99)
        # each covering at least 0.1% of values, e.g. 9.9 alongside 9.9%
        fmt = nonblank.map(lambda v: re.sub(r"9+", "9", value_shape(v)).lstrip("-")).value_counts()
        material_shapes = int((fmt / max(len(nonblank), 1) >= 0.001).sum())
        fail = ~parses_as(nonblank, typ) if typ != "text" else pd.Series(False, index=nonblank.index)
        nums = to_num(nonblank) if typ in ("int", "float") else pd.Series(dtype=float)
        rows.append({
            "table": table,
            "column": col,
            "rows": len(s),
            "expected_type": typ,
            "blank_count": int(blank.sum()),
            "blank_pct": round(blank.mean() * 100, 3),
            "null_word_count": int(null_words.sum()),
            "distinct_count": int(s.nunique()),
            "distinct_pct": round(s.nunique() / max(len(s), 1) * 100, 3),
            "top_shapes": top,
            "shape_count": int(len(shapes)),
            "formats": "; ".join(f"{k} ({v / max(len(nonblank), 1):.1%})" for k, v in fmt.head(3).items()),
            "mixed_format": material_shapes > 1 and typ != "text",
            "minority_format_count": int(len(nonblank) - fmt.iloc[0]) if len(fmt) else 0,
            "parse_fail_count": int(fail.sum()),
            "parse_fail_pct": round(fail.mean() * 100, 3) if len(nonblank) else 0.0,
            "parse_fail_examples": "; ".join(nonblank[fail].unique()[:3]),
            "whitespace_issues": int((s != s.str.strip()).sum() + s.str.contains(r"\s{2,}").sum()),
            "numeric_min": nums.min() if len(nums) else "",
            "numeric_max": nums.max() if len(nums) else "",
            "top_values": "; ".join(f"{k}={v}" for k, v in s.value_counts().head(5).items()),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Findings collector
# --------------------------------------------------------------------------
FINDINGS = []


def add(table, column, group, check, severity, rows_affected, total, example="", detail=""):
    """Record one finding. rows_affected=0 findings are kept as passes (severity PASS)."""
    FINDINGS.append({
        "table": table,
        "column": column,
        "check_group": group,
        "check": check,
        "severity": severity if rows_affected else "PASS",
        "rows_affected": int(rows_affected),
        "pct_of_rows": round(rows_affected / max(total, 1) * 100, 3),
        "example": str(example)[:200],
        "detail": detail,
    })


def ex(df, mask, cols, n=2):
    """Short example string from the first rows matching mask."""
    return " | ".join(", ".join(f"{c}={r[c]}" for c in cols) for _, r in df[mask].head(n).iterrows())


# --------------------------------------------------------------------------
# Group 1: column level
# --------------------------------------------------------------------------
def column_checks(T):
    for t, sch in SCHEMA.items():
        df, n = T[t], len(T[t])
        for col, spec in sch["columns"].items():
            s = df[col]
            blank = s.str.strip() == ""
            if blank.any():
                add(t, col, "1 column", "blank values", "INFO" if spec.get("nullable") else "WARN",
                    blank.sum(), n, detail="nullable by design: confirm with a rule" if spec.get("nullable")
                    else "column is not expected to be blank")
            v = s[~blank]
            if spec["type"] != "text":
                bad = ~parses_as(v, spec["type"])
                add(t, col, "1 column", f"type validity ({spec['type']})", "ERROR", bad.sum(), n,
                    "; ".join(v[bad].unique()[:4]), "value does not parse as the expected type")
            if "allowed" in spec:
                bad = ~v.isin(spec["allowed"])
                add(t, col, "1 column", "allowed values", "ERROR", bad.sum(), n,
                    "; ".join(v[bad].value_counts().head(5).index), "value outside the allowed code list")
            if "pattern" in spec:
                bad = ~v.str.match(spec["pattern"])
                add(t, col, "1 column", "pattern", "ERROR", bad.sum(), n, "; ".join(v[bad].unique()[:4]))
            if "min" in spec or "max" in spec:
                if spec["type"] == "date":
                    vals = v[parses_as(v, "date")]
                    lo = vals < spec.get("min", "0000") if "min" in spec else pd.Series(False, index=vals.index)
                    hi = vals > spec.get("max", "9999") if "max" in spec else pd.Series(False, index=vals.index)
                else:
                    # only values that parse; unparseable ones are already counted by type validity
                    vals = to_num(v.where(parses_as(v, "float"), ""))
                    lo = vals < spec["min"] if "min" in spec else pd.Series(False, index=vals.index)
                    hi = vals > spec["max"] if "max" in spec else pd.Series(False, index=vals.index)
                out = lo | hi
                add(t, col, "1 column", f"range [{spec.get('min', '')}, {spec.get('max', '')}]", "ERROR",
                    out.sum(), n, "; ".join(v[out].astype(str).unique()[:4]))
        # key uniqueness
        pk = sch["pk"]
        add(t, pk, "1 column", "primary key unique", "ERROR", df[pk].duplicated().sum(), n)
        add(t, pk, "1 column", "primary key not blank", "ERROR", (df[pk].str.strip() == "").sum(), n)
        for u in sch.get("unique", []):
            add(t, u, "1 column", "natural key unique", "ERROR", df[u].duplicated().sum(), n)


# --------------------------------------------------------------------------
# Group 2: single-table rules
# --------------------------------------------------------------------------
def single_table_checks(T):
    for t, sch in SCHEMA.items():
        df, n = T[t], len(T[t])
        pk = sch["pk"]
        d = df.drop(columns=pk).duplicated(keep="first")
        add(t, "(all)", "2 single-table", "exact duplicate rows (ignoring PK)", "ERROR", d.sum(), n)
        if "grain" in sch:
            g = df.duplicated(sch["grain"], keep="first")
            add(t, "+".join(sch["grain"]), "2 single-table", "one row per grain", "ERROR", g.sum(), n)

    # near-duplicate clients: identical except id and last name
    c = T["dim_client"]
    cols = SCHEMA["dim_client"]["near_dup_cols"]
    nd = c.duplicated(cols, keep=False)
    later = c.duplicated(cols, keep="first")
    pairs = c[nd].sort_values(cols + ["client_id"]).groupby(cols, sort=False)
    sample = "; ".join(f"{'/'.join(g.client_id)}: {'/'.join(g.last_name)}" for _, g in list(pairs)[:3])
    add("dim_client", "client_id", "2 single-table", "near-duplicate clients (all fields equal except id, last_name)",
        "ERROR", later.sum(), len(c), sample, f"{nd.sum()} rows form {later.sum()} pairs")

    # dim_security: ETFs have expense ratio and no sector; stocks the reverse
    s = T["dim_security"]
    etf = s.is_etf == "True"
    add("dim_security", "sector", "2 single-table", "sector blank only for ETFs", "ERROR",
        ((s.sector == "") & ~etf).sum() + ((s.sector != "") & etf).sum(), len(s))
    add("dim_security", "expense_ratio_bps", "2 single-table", "expense ratio present only for ETFs", "ERROR",
        ((s.expense_ratio_bps == "") & etf).sum() + ((s.expense_ratio_bps != "") & ~etf).sum(), len(s))
    add("dim_security", "sector", "2 single-table", "INFO: blank sector is structural (ETF)", "INFO",
        (s.sector == "").sum(), len(s), detail="legitimate structure, not a defect")
    dn = s.name.duplicated(keep=False)
    add("dim_security", "name", "2 single-table", "same name, different ticker", "INFO", dn.sum(), len(s),
        ex(s, dn, ["security_id", "ticker", "name", "asset_class"]), "different tickers / asset classes: likely distinct funds")

    # dim_client: tier should match initial AUM band
    c = T["dim_client"].copy()
    a = to_num(c.initial_aum)
    band = np.select([a < 500_000, a < 5_000_000], ["Retail", "HNW"], "UHNW")
    add("dim_client", "client_tier", "2 single-table", "tier matches initial_aum band (<500k / <5M / 5M+)",
        "WARN", (c.client_tier != band).sum(), len(c))

    # dim_date: every attribute must agree with the date itself
    d = T["dim_date"]
    dt = pd.to_datetime(d.date, errors="coerce")
    derived = {
        "year": dt.dt.year, "quarter": dt.dt.quarter, "month": dt.dt.month, "month_name": dt.dt.month_name(),
        "day_of_week": dt.dt.day_name(), "week_of_year": dt.dt.isocalendar().week.astype(int),
        "is_month_end": dt.dt.is_month_end.astype(int), "is_quarter_end": dt.dt.is_quarter_end.astype(int),
        "is_year_end": dt.dt.is_year_end.astype(int), "is_trading_day": (dt.dt.dayofweek < 5).astype(int),
    }
    for col, v in derived.items():
        add("dim_date", col, "2 single-table", "attribute agrees with date", "ERROR",
            (d[col].values != v.astype(str).values).sum(), len(d))
    gaps = (dt.diff().dropna().dt.days != 1).sum()
    add("dim_date", "date", "2 single-table", "calendar is contiguous (no missing days)", "ERROR", gaps, len(d))
    add("dim_date", "is_trading_day", "2 single-table", "INFO: trading day = weekday (market holidays not excluded)",
        "INFO", ((dt.dt.month == 12) & (dt.dt.day == 25) & (dt.dt.dayofweek < 5)).sum(), len(d),
        detail="e.g. Christmas on a weekday is marked as a trading day")

    # fact_fees: amount = aum_basis * bps / 10,000 / 12
    f = T["fact_fees"]
    calc = (to_num(f.aum_basis) * to_num(f.bps_charged) / 10000 / 12).round(2)
    bad = (to_num(f.amount) - calc).abs() > 0.011
    add("fact_fees", "amount", "2 single-table", "amount = aum_basis x bps / 10,000 / 12", "ERROR", bad.sum(), len(f))

    # fact_portfolio_snapshot: alpha = return - benchmark, year/month agree with date
    p = T["fact_portfolio_snapshot"]
    r = to_num(p.return_ytd)
    alpha_bad = (to_num(p.active_alpha_ytd) - (r - to_num(p.benchmark_return_ytd))).abs() > 2e-6
    add("fact_portfolio_snapshot", "active_alpha_ytd", "2 single-table",
        "alpha = return_ytd - benchmark_return_ytd (numeric rows)", "ERROR", alpha_bad.sum(), len(p))
    pct = p.return_ytd.str.endswith("%")
    if pct.any():
        implied = to_num(p.active_alpha_ytd) + to_num(p.benchmark_return_ytd)
        match = (to_num(p.return_ytd.str.rstrip("%")) / 100 - implied).abs() <= 0.00006
        add("fact_portfolio_snapshot", "return_ytd", "2 single-table",
            "percent-text values: does value/100 equal alpha + benchmark?", "INFO", (pct & match).sum(), len(p),
            ex(p, pct, ["snapshot_id", "return_ytd", "benchmark_return_ytd", "active_alpha_ytd"]),
            f"{(pct & match).sum()} of {pct.sum()} percent values reconcile after /100")
    add("fact_portfolio_snapshot", "year", "2 single-table", "year agrees with snapshot_date", "ERROR",
        (p.year != p.snapshot_date.str[:4]).sum(), len(p))
    add("fact_portfolio_snapshot", "month", "2 single-table", "month agrees with snapshot_date", "ERROR",
        (to_num(p.month) != to_num(p.snapshot_date.str[5:7])).sum(), len(p))
    add("fact_portfolio_snapshot", "snapshot_date", "2 single-table", "snapshot dated on the 1st", "ERROR",
        (~p.snapshot_date.str.endswith("-01")).sum(), len(p))
    floor = to_num(p.aum) == 1000
    add("fact_portfolio_snapshot", "aum", "2 single-table", "aum sits exactly at 1,000.00 (floor value)", "WARN",
        floor.sum(), len(p), ex(p, floor, ["client_id", "snapshot_date", "aum", "return_ytd"]),
        "same value repeated month after month with ~-96% returns: looks like a system floor, not a real balance")
    big = r.abs() > 1
    add("fact_portfolio_snapshot", "return_ytd", "2 single-table", "|return_ytd| > 100% (numeric rows)", "WARN",
        big.sum(), len(p), ex(p, big, ["client_id", "snapshot_date", "return_ytd"]),
        "plausibility: extreme but alpha reconciles and series are continuous month to month")

    # fact_transactions: null pattern and sign rules by txn_type
    x = T["fact_transactions"]
    cash = x.txn_type.isin(CASH_TXN_TYPES)
    secx = x.txn_type.isin(SECURITY_TXN_TYPES)
    sec_fields_blank = (x.security_id == "") & (x.shares == "") & (x.price == "")
    add("fact_transactions", "security_id/shares/price", "2 single-table",
        "cash txns have no security/shares/price", "ERROR", (cash & ~sec_fields_blank).sum(), len(x))
    add("fact_transactions", "security_id/shares/price", "2 single-table",
        "security txns have security/shares/price", "ERROR",
        (secx & ((x.security_id == "") | (x.shares == "") | (x.price == ""))).sum(), len(x))
    add("fact_transactions", "security_id/shares/price", "2 single-table",
        "INFO: blanks on cash txns are structural", "INFO", (cash & sec_fields_blank).sum(), len(x),
        detail="Deposit / Withdrawal / Advisory Fee have no security: legitimate, do not fill")
    sh, px, amt = to_num(x.shares), to_num(x.price), to_num(x.amount)
    neg = secx & (sh < 0)
    add("fact_transactions", "shares", "2 single-table", "shares negative on security txn", "ERROR", neg.sum(), len(x),
        ex(x, neg, ["txn_id", "txn_type", "shares", "price", "amount"]),
        f"by type: {x[neg].txn_type.value_counts().to_dict()}")
    recon = secx & ((amt - (sh * px).round(2)).abs() > 0.011)
    add("fact_transactions", "amount", "2 single-table", "amount = shares x price", "ERROR", recon.sum(), len(x),
        ex(x, recon, ["txn_id", "shares", "price", "amount"]))
    recon_abs = secx & ((amt - (sh.abs() * px).round(2)).abs() > 0.011)
    add("fact_transactions", "amount", "2 single-table", "amount = |shares| x price", "ERROR", recon_abs.sum(), len(x),
        detail="if this passes while the signed check fails, the sign of shares is the defect, not the amount")
    # running position per client-security: can a Sell exceed what was bought before it?
    tr = x[x.txn_type.isin(["Buy", "Sell"])].assign(q=sh.abs()).sort_values(["txn_date", "txn_id"])
    tr["pos"] = (tr.q * np.where(tr.txn_type == "Buy", 1, -1)).groupby([tr.client_id, tr.security_id]).cumsum()
    oversell = (tr.txn_type == "Sell") & (tr.pos < -1e-6)
    add("fact_transactions", "shares", "2 single-table", "Sell exceeds position built from earlier Buys", "INFO",
        oversell.sum(), len(x), detail=f"{oversell.sum()} of {(tr.txn_type == 'Sell').sum()} sells; "
        "extract has no opening holdings, so positions cannot be reconstructed")


# --------------------------------------------------------------------------
# Group 3: referential integrity
# --------------------------------------------------------------------------
def ri_checks(T):
    for ft, fk, dt_, dk in RELATIONSHIPS:
        f, d = T[ft], T[dt_]
        vals = f[fk]
        nonblank = vals.str.strip() != ""
        orphan = nonblank & ~vals.isin(set(d[dk]))
        add(ft, fk, "3 referential", f"{fk} -> {dt_}.{dk} (exact text match)", "ERROR", orphan.sum(), len(f),
            "; ".join(vals[orphan].value_counts().head(4).index),
            f"{vals[orphan].nunique()} distinct orphan keys; {(~nonblank).sum()} blank keys")
        if orphan.any() and fk.endswith("_id"):
            # does the join work once the key is normalised to an integer?
            norm = to_num(vals).dropna().astype("int64").astype(str)
            still = (~norm.isin(set(d[dk]))).sum()
            add(ft, fk, "3 referential", f"{fk} -> {dt_}.{dk} (after numeric normalisation)", "ERROR",
                still, len(f), "; ".join(norm[~norm.isin(set(d[dk]))].value_counts().head(4).index),
                "orphans remaining after 45.0 -> 45; the rest of the gap is a format problem")


# --------------------------------------------------------------------------
# Group 4: cross-table business rules
# --------------------------------------------------------------------------
def cross_table_checks(T):
    c = T["dim_client"].set_index("client_id")
    f, p, x = T["fact_fees"], T["fact_portfolio_snapshot"], T["fact_transactions"]
    known = x.client_id.isin(c.index)

    for t, df in [("fact_fees", f), ("fact_portfolio_snapshot", p), ("fact_transactions", x)]:
        k = df.client_id.isin(c.index)
        bad = k & (df.advisor_id != df.client_id.map(c.advisor_id))
        add(t, "advisor_id", "4 cross-table", "advisor matches the client's advisor in dim_client", "ERROR",
            bad.sum(), len(df))

    add("fact_portfolio_snapshot", "account_type", "4 cross-table", "account_type = client primary_account_type",
        "ERROR", (p.account_type != p.client_id.map(c.primary_account_type)).sum(), len(p))

    # fees use the same AUM as the snapshot for that client-month
    j = f.merge(p[["client_id", "snapshot_date", "aum"]], left_on=["client_id", "fee_date"],
                right_on=["client_id", "snapshot_date"], how="left")
    add("fact_fees", "aum_basis", "4 cross-table", "fee has a snapshot for the same client-month", "ERROR",
        j.aum.isna().sum(), len(f))
    add("fact_fees", "aum_basis", "4 cross-table", "aum_basis = snapshot aum for that client-month", "ERROR",
        (j.aum.notna() & (to_num(j.aum_basis) != to_num(j.aum))).sum(), len(f))
    k = p.merge(f[["client_id", "fee_date"]], left_on=["client_id", "snapshot_date"],
                right_on=["client_id", "fee_date"], how="left")
    add("fact_portfolio_snapshot", "snapshot_date", "4 cross-table", "snapshot month has no fee row", "INFO",
        k.fee_date.isna().sum(), len(p), detail="fee not billed that month (waiver / timing); not a defect by itself")

    # benchmark follows risk profile
    risk = p.client_id.map(c.risk_profile)
    expected = risk.map({"Aggressive": "1", "Moderately Aggressive": "1", "Balanced": "3",
                         "Moderately Conservative": "8", "Conservative": "8"})
    add("fact_portfolio_snapshot", "benchmark_id", "4 cross-table", "benchmark consistent with client risk_profile",
        "ERROR", (expected.notna() & (p.benchmark_id != expected)).sum(), len(p))
    blank_risk = risk == ""
    add("fact_portfolio_snapshot", "benchmark_id", "4 cross-table",
        "snapshots of clients with blank risk_profile: benchmark assigned", "INFO", blank_risk.sum(), len(p),
        f"benchmark_id values: {p[blank_risk].benchmark_id.value_counts().to_dict()}",
        "blank-risk clients all sit on benchmark 3: looks like a default, not evidence they are Balanced")

    # timing rules
    since = x.client_id.map(c.client_since)
    add("fact_transactions", "txn_date", "4 cross-table", "txn on/after client_since", "ERROR",
        (known & (x.txn_date < since)).sum(), len(x))
    last = p.groupby("client_id").snapshot_date.max()
    after = known & (x.txn_date.str[:7] > x.client_id.map(last).str[:7])
    add("fact_transactions", "txn_date", "4 cross-table", "txn after the client's last snapshot month", "WARN",
        after.sum(), len(x), ex(x, after, ["txn_id", "client_id", "txn_date", "txn_type"]),
        f"is_active of those clients: {x[after].client_id.map(c.is_active).value_counts().to_dict()}")
    trade_day = x.txn_date.map(T["dim_date"].set_index("date").is_trading_day)
    wk = x.txn_type.isin(["Buy", "Sell"]) & (trade_day == "0")
    add("fact_transactions", "txn_date", "4 cross-table", "Buy/Sell on a non-trading day (dim_date)", "WARN",
        wk.sum(), len(x), ex(x, wk, ["txn_id", "txn_type", "txn_date"]))

    # advisory-fee debits in transactions vs charges in fact_fees
    adv = x[x.txn_type == "Advisory Fee"].assign(m=x.txn_date.str[:7], a=to_num(x.amount))
    fee_m = f.assign(m=f.fee_date.str[:7], a=to_num(f.amount)).groupby(["client_id", "m"]).a.sum()
    adv_m = adv.groupby(["client_id", "m"]).a.sum()
    both = adv_m.to_frame("txn").join(fee_m.rename("fee"), how="inner")
    off = (both.txn - both.fee).abs() > 0.01
    add("fact_transactions", "amount", "4 cross-table",
        "Advisory Fee debits = fact_fees charges (same client-month)", "WARN", off.sum(), len(both),
        detail=f"median ratio txn/fee = {(both.txn / both.fee).median():.2f}; rows compared = client-months in both")

    # initial AUM vs first snapshot
    first = p.sort_values("snapshot_date").groupby("client_id").first()
    ratio = to_num(first.aum) / to_num(first.index.to_series().map(c.initial_aum))
    add("fact_portfolio_snapshot", "aum", "4 cross-table", "first snapshot aum within 50% of initial_aum", "WARN",
        ((ratio < 0.5) | (ratio > 1.5)).sum(), len(first))

    # dimension members with no activity
    for t, df in [("fact_fees", f), ("fact_portfolio_snapshot", p), ("fact_transactions", x)]:
        unused = ~c.index.isin(set(df.client_id))
        add("dim_client", "client_id", "4 cross-table", f"client has no rows in {t}", "INFO", unused.sum(), len(c),
            "; ".join(c.index[unused][:5]))


# --------------------------------------------------------------------------
def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # single-file mode: generic profile only, proves the profiler is not table-specific
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        print(profile_table(df, path.stem).to_string())
        return

    T = load_tables(RAW_DIR)
    profile = pd.concat([profile_table(df, t, SCHEMA.get(t)) for t, df in T.items()], ignore_index=True)
    profile.to_csv(REPORTS_DIR / "profile_raw.csv", index=False)

    # generic findings straight from the profile (no column names involved)
    for _, r in profile.iterrows():
        if r.mixed_format:
            add(r.table, r.column, "1 column", "mixed formats in one column", "WARN", r.minority_format_count,
                r.rows, r.formats)
        if r.whitespace_issues:
            add(r.table, r.column, "1 column", "leading/trailing/double whitespace", "WARN", r.whitespace_issues, r.rows)
        if r.null_word_count:
            add(r.table, r.column, "1 column", "null-like words (None/NULL/N/A)", "INFO", r.null_word_count, r.rows,
                detail="pd.read_csv defaults would turn these into NaN: check whether the word is a real value")

    column_checks(T)
    single_table_checks(T)
    ri_checks(T)
    cross_table_checks(T)
    dq = pd.DataFrame(FINDINGS)
    order = {"ERROR": 0, "WARN": 1, "INFO": 2, "PASS": 3}
    dq = dq.sort_values(["severity", "check_group", "table"], key=lambda s: s.map(order) if s.name == "severity" else s)
    dq.to_csv(REPORTS_DIR / "dq_summary_raw.csv", index=False)

    print(f"Profiled {len(T)} tables, {len(profile)} columns -> reports/profile_raw.csv")
    print(f"{len(dq)} checks -> reports/dq_summary_raw.csv")
    print(dq.severity.value_counts().to_string())
    print("\nFindings (excluding PASS):")
    pd.set_option("display.width", 250)
    print(dq[dq.severity != "PASS"][["severity", "table", "column", "check", "rows_affected", "pct_of_rows"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
