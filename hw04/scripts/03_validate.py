"""
HW4 Part D: referential integrity, rule checks, reconciliations, outliers, scorecard.

Runs every check on BOTH the raw and the clean tables so each number has a
before and after.

  check_referential_integrity()  one reusable function (kept for Assignment 5),
                                 applied to all 13 relationships
  rule checks                    allowed codes, ranges, patterns, sign rules
  reconciliations                recomputed values vs stored values, and
                                 cross-table agreement
  IQR outliers                   numeric columns with no natural upper bound

Outputs (reports/):
  data_quality_scorecard.csv   one row per table per stage
  ri_results.csv               13 relationships x 2 stages
  rule_results.csv             every rule x 2 stages
  reconciliations.csv          every reconciliation x 2 stages
  outliers_iqr.csv             IQR fences and counts x 2 stages

Usage:  python hw04/scripts/03_validate.py
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wildcat_schema import (CASH_TXN_TYPES, CLEAN_DIR, RAW_DIR, RELATIONSHIPS, REPORTS_DIR, SCHEMA,
                            SECURITY_TXN_TYPES, TABLES, load_tables)


# ==========================================================================
# Reusable referential-integrity check (Assignment 5 reuses this as-is)
# ==========================================================================
def check_referential_integrity(fact_df, fact_key, dim_df, dim_key):
    """
    Check that every non-null foreign key in fact_df[fact_key] exists in dim_df[dim_key].

    Blank strings and NaN both count as null keys. Null keys are reported
    separately and excluded from the match rate, because a null key (e.g. no
    security on a deposit) is a modelling question, not an orphan.

    Returns a dict:
      fact_rows            rows in fact_df
      null_key_rows        rows with a null / blank key
      null_key_rate        null_key_rows / fact_rows
      matched_rows         non-null keys found in the dimension
      orphan_rows          non-null keys NOT found in the dimension
      distinct_orphan_keys number of distinct orphan key values
      match_rate           matched_rows / non-null rows (1.0 if there are none)
      orphan_examples      up to 5 orphan key values
      dim_key_unique       True if dim_key is unique (required for many-to-one)
    """
    keys = fact_df[fact_key]
    is_null = keys.isna() | (keys.astype(str).str.strip() == "")
    valid = set(dim_df[dim_key].dropna().astype(str))
    present = keys[~is_null].astype(str)
    orphan = ~present.isin(valid)
    n_nonnull = int((~is_null).sum())
    return {
        "fact_rows": len(fact_df),
        "null_key_rows": int(is_null.sum()),
        "null_key_rate": round(is_null.mean(), 6) if len(fact_df) else 0.0,
        "matched_rows": int((~orphan).sum()),
        "orphan_rows": int(orphan.sum()),
        "distinct_orphan_keys": int(present[orphan].nunique()),
        "match_rate": round((~orphan).sum() / n_nonnull, 6) if n_nonnull else 1.0,
        "orphan_examples": "; ".join(present[orphan].value_counts().head(5).index),
        "dim_key_unique": bool(dim_df[dim_key].is_unique),
    }


# ==========================================================================
# Helpers
# ==========================================================================
INT_RE, FLOAT_RE = r"^-?\d+$", r"^-?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$"


def num(s):
    return pd.to_numeric(s.where(s.astype(str).str.strip() != ""), errors="coerce")


def parses(s, typ):
    if typ == "int":
        return s.str.match(INT_RE)
    if typ == "float":
        return s.str.match(FLOAT_RE)
    if typ == "date":
        return pd.to_datetime(s, format="%Y-%m-%d", errors="coerce").notna()
    if typ == "bool":
        return s.isin(["True", "False"])
    if typ == "flag01":
        return s.isin(["0", "1"])
    return pd.Series(True, index=s.index)


# ==========================================================================
# Rule checks: each returns a boolean Series (True = row passes) per rule
# ==========================================================================
def column_rules(t, df):
    """Allowed codes, ranges and patterns from the schema, tested on non-blank values.
    Blanks pass here because they are scored once, under completeness."""
    rules = {}
    for col, spec in SCHEMA[t]["columns"].items():
        s = df[col]
        blank = s.str.strip() == ""
        if "allowed" in spec:
            rules[f"{col} in allowed list"] = blank | s.isin(spec["allowed"])
        if "pattern" in spec:
            rules[f"{col} matches {spec['pattern']}"] = blank | s.str.match(spec["pattern"])
        if "min" in spec or "max" in spec:
            if spec["type"] == "date":
                ok = parses(s, "date") & (s >= spec.get("min", "0000")) & (s <= spec.get("max", "9999"))
            else:
                v = num(s.where(parses(s, "float"), ""))
                ok = v.notna()
                if "min" in spec:
                    ok &= v >= spec["min"]
                if "max" in spec:
                    ok &= v <= spec["max"]
            rules[f"{col} in range [{spec.get('min', '')}, {spec.get('max', '')}]"] = ok | blank
    return rules


def row_rules(t, df, T):
    """Business rules within a row (sign rules, structure, recomputable columns)."""
    r = {}
    if t == "dim_client":
        a = num(df.initial_aum)
        band = np.select([a < 500_000, a < 5_000_000], ["Retail", "HNW"], "UHNW")
        r["client_tier matches initial_aum band"] = pd.Series(df.client_tier.values == band, index=df.index)
    if t == "dim_security":
        etf = df.is_etf == "True"
        r["ETF: expense ratio, no sector; stock: sector, no expense ratio"] = \
            (etf & (df.sector == "") & (df.expense_ratio_bps != "")) | (~etf & (df.sector != "") & (df.expense_ratio_bps == ""))
    if t == "fact_fees":
        calc = (num(df.aum_basis) * num(df.bps_charged) / 10000 / 12).round(2)
        r["amount = aum_basis x bps / 10,000 / 12"] = (num(df.amount) - calc).abs() <= 0.011
    if t == "fact_portfolio_snapshot":
        r["year/month agree with snapshot_date"] = (df.year == df.snapshot_date.str[:4]) & \
            (num(df.month) == num(df.snapshot_date.str[5:7]))
    if t == "fact_transactions":
        cash = df.txn_type.isin(CASH_TXN_TYPES)
        blanks = (df.security_id == "") & (df.shares == "") & (df.price == "")
        r["cash txn has no security; security txn has all three"] = (cash & blanks) | \
            (~cash & (df.security_id != "") & (df.shares != "") & (df.price != ""))
        r["sign rule: shares >= 0 and amount > 0"] = ((num(df.shares) >= 0) | (df.shares == "")) & (num(df.amount) > 0)
    for flag in [c for c in df.columns if c.endswith("_flag")]:
        r[f"{flag} is 0/1"] = df[flag].isin(["0", "1"])
    return r


# ==========================================================================
# Reconciliations: recomputed vs stored, and table vs table
# ==========================================================================
def reconciliations(T):
    out = []
    f, p, x, c = T["fact_fees"], T["fact_portfolio_snapshot"], T["fact_transactions"], T["dim_client"]

    def rec(name, kind, passed, compared, detail=""):
        out.append({"reconciliation": name, "type": kind, "rows_compared": int(compared), "rows_agree": int(passed),
                    "agree_pct": round(passed / compared * 100, 3) if compared else 100.0, "detail": detail})

    # 1 recomputed: transaction amount = shares x price
    sec = x[x.txn_type.isin(SECURITY_TXN_TYPES)]
    ok = (num(sec.amount) - (num(sec.shares) * num(sec.price)).round(2)).abs() <= 0.011
    rec("txn amount = shares x price (Buy/Sell/Dividend)", "recomputed", ok.sum(), len(sec))

    # 2 recomputed: fee amount = aum_basis x bps / 120,000
    ok = (num(f.amount) - (num(f.aum_basis) * num(f.bps_charged) / 120000).round(2)).abs() <= 0.011
    rec("fee amount = aum_basis x bps / 10,000 / 12", "recomputed", ok.sum(), len(f))

    # 3 recomputed: alpha = return - benchmark (non-numeric returns count as disagreeing)
    r = num(p.return_ytd)
    ok = (num(p.active_alpha_ytd) - (r - num(p.benchmark_return_ytd))).abs() <= 2e-6
    rec("active_alpha_ytd = return_ytd - benchmark_return_ytd (tol 0.000002)", "recomputed", ok.sum(), len(p),
        f"{r.isna().sum()} return values not numeric")
    # same check at the precision of a 2-decimal percent (9.28% = 0.0928 +/- 0.00005)
    ok = (num(p.active_alpha_ytd) - (r - num(p.benchmark_return_ytd))).abs() <= 0.00006
    rec("active_alpha_ytd = return_ytd - benchmark_return_ytd (tol 0.00006)", "recomputed", ok.sum(), len(p),
        "tolerance covers values converted from 2-decimal percent text (D17)")

    # 4 cross-table: fee aum_basis = snapshot aum for the same client-month
    j = f.merge(p[["client_id", "snapshot_date", "aum"]], left_on=["client_id", "fee_date"],
                right_on=["client_id", "snapshot_date"], how="left")
    ok = num(j.aum_basis) == num(j.aum)
    rec("fact_fees.aum_basis = fact_portfolio_snapshot.aum (client-month)", "cross-table", ok.sum(), len(j))

    # 5 cross-table: advisor on every fact = client's advisor in dim_client
    adv = c.set_index("client_id").advisor_id
    agree = total = 0
    for df in (f, p, x):
        agree += (df.advisor_id == df.client_id.map(adv)).sum()
        total += len(df)
    rec("fact advisor_id = dim_client.advisor_id (all 3 facts)", "cross-table", agree, total,
        "rows whose client is missing from dim_client count as disagreeing")

    # 6 cross-table: snapshot account_type = client's primary_account_type
    ok = p.account_type == p.client_id.map(c.set_index("client_id").primary_account_type)
    rec("snapshot account_type = dim_client.primary_account_type", "cross-table", ok.sum(), len(p))

    # 7 cross-table: Advisory Fee debits vs fee charges (documented disagreement, D15)
    adv_m = x[x.txn_type == "Advisory Fee"].assign(m=x.txn_date.str[:7], a=num(x.amount)).groupby(["client_id", "m"]).a.sum()
    fee_m = f.assign(m=f.fee_date.str[:7], a=num(f.amount)).groupby(["client_id", "m"]).a.sum()
    both = adv_m.to_frame("txn").join(fee_m.rename("fee"), how="inner")
    rec("Advisory Fee txns = fact_fees amount (client-month)", "cross-table",
        ((both.txn - both.fee).abs() <= 0.01).sum(), len(both),
        f"median txn/fee ratio {(both.txn / both.fee).median():.2f}; totals: Advisory Fee txns "
        f"${num(x.amount[x.txn_type == 'Advisory Fee']).sum():,.2f} vs fact_fees ${num(f.amount).sum():,.2f} "
        f"({num(x.amount[x.txn_type == 'Advisory Fee']).sum() / num(f.amount).sum():.2f}x); known limitation D15")
    return out


# ==========================================================================
# IQR outliers on columns with no natural upper bound
# ==========================================================================
IQR_COLUMNS = [("fact_transactions", "amount"), ("fact_portfolio_snapshot", "aum"),
               ("fact_portfolio_snapshot", "return_ytd")]


def iqr_outliers(T):
    out = []
    for t, col in IQR_COLUMNS:
        v = num(T[t][col]).dropna()
        q1, q3 = v.quantile([0.25, 0.75])
        lo, hi = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
        flagged = (v < lo) | (v > hi)
        # who are the flagged rows? (helps judge "outlier" vs "wrong")
        tier = T[t].loc[flagged[flagged].index, "client_id"].map(T["dim_client"].set_index("client_id").client_tier)
        mix = "; ".join(f"{k} {p:.1%}" for k, p in tier.value_counts(normalize=True).items())
        out.append({"table": t, "column": col, "values": len(v), "q1": q1, "q3": q3, "lower_fence": lo,
                    "upper_fence": hi, "below": int((v < lo).sum()), "above": int((v > hi).sum()),
                    "flagged": int(flagged.sum()), "flagged_pct": round(flagged.mean() * 100, 3),
                    "max_value": v.max(), "flagged_client_tier_mix": mix})
    # plausibility: returns above +/-100% (D20), with tier mix
    r = num(T["fact_portfolio_snapshot"].return_ytd)
    big = r.abs() > 1
    tier = T["fact_portfolio_snapshot"].client_id[big].map(T["dim_client"].set_index("client_id").client_tier)
    out.append({"table": "fact_portfolio_snapshot", "column": "return_ytd (|value| > 1, D20)", "values": int(r.notna().sum()),
                "flagged": int(big.sum()), "flagged_pct": round(big.mean() * 100, 3), "max_value": r.max(),
                "flagged_client_tier_mix": "; ".join(f"{k} {p:.1%}" for k, p in tier.value_counts(normalize=True).items())})
    return out


# ==========================================================================
# Scorecard
# ==========================================================================
def key_sets(t):
    sch = SCHEMA[t]
    sets = [[sch["pk"]]] + [[u] for u in sch.get("unique", [])]
    for k in ("grain", "near_dup_cols"):
        if k in sch:
            sets.append(sch[k])
    return sets


def score_table(t, df, T):
    cols = SCHEMA[t]["columns"]
    # completeness: non-blank cells in columns that are not blank-by-design
    req = [c for c, s in cols.items() if not s.get("nullable")]
    completeness = (df[req].apply(lambda s: s.str.strip() != "")).values.mean()
    # key uniqueness: rows not duplicated on any declared key (PK, natural key, grain, near-dup match)
    dup = pd.Series(False, index=df.index)
    for ks in key_sets(t):
        dup |= df.duplicated(ks, keep="first")
    uniqueness = 1 - dup.mean()
    # type validity: non-blank cells that parse as the declared type
    ok = total = 0
    for c, s in cols.items():
        v = df[c][df[c].str.strip() != ""]
        ok += parses(v, s["type"]).sum()
        total += len(v)
    validity = ok / total
    # rule pass: rows passing every column and row rule
    rules = {**column_rules(t, df), **row_rules(t, df, T)}
    passing = pd.concat(rules.values(), axis=1).all(axis=1) if rules else pd.Series(True, index=df.index)
    # referential match: rows whose every FK (non-null) resolves
    fks = [(fk, d, dk) for ft, fk, d, dk in RELATIONSHIPS if ft == t]
    if fks:
        ref_ok = pd.Series(True, index=df.index)
        for fk, d, dk in fks:
            blank = df[fk].str.strip() == ""
            ref_ok &= blank | df[fk].isin(set(T[d][dk]))
        ref = ref_ok.mean()
    else:
        ref = np.nan
    return {
        "rows": len(df),
        "pct_completeness": round(completeness * 100, 3),
        "pct_key_uniqueness": round(uniqueness * 100, 3),
        "pct_type_validity": round(validity * 100, 3),
        "pct_rule_pass": round(passing.mean() * 100, 3),
        "pct_referential_match": round(ref * 100, 3) if fks else "n/a (no foreign keys)",
    }, rules


# ==========================================================================
def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stages = {"raw": load_tables(RAW_DIR), "clean": load_tables(CLEAN_DIR)}
    score, ri, rule_rows, recon, iqr = [], [], [], [], []

    for stage, T in stages.items():
        for ft, fk, dt, dk in RELATIONSHIPS:
            res = check_referential_integrity(T[ft], fk, T[dt], dk)
            ri.append({"stage": stage, "relationship": f"{ft}.{fk} -> {dt}.{dk}", **res})
        for t in TABLES:
            s, rules = score_table(t, T[t], T)
            score.append({"table": t, "stage": stage, **s})
            for name, passed in rules.items():
                rule_rows.append({"stage": stage, "table": t, "rule": name, "rows": len(passed),
                                  "fail_rows": int((~passed).sum()), "pass_pct": round(passed.mean() * 100, 3)})
        recon += [{"stage": stage, **r} for r in reconciliations(T)]
        iqr += [{"stage": stage, **r} for r in iqr_outliers(T)]

    sc = pd.DataFrame(score).sort_values(["table", "stage"], ascending=[True, False])
    ri_df, rules_df, rec_df, iqr_df = map(pd.DataFrame, (ri, rule_rows, recon, iqr))
    sc.to_csv(REPORTS_DIR / "data_quality_scorecard.csv", index=False)
    ri_df.to_csv(REPORTS_DIR / "ri_results.csv", index=False)
    rules_df.to_csv(REPORTS_DIR / "rule_results.csv", index=False)
    rec_df.to_csv(REPORTS_DIR / "reconciliations.csv", index=False)
    iqr_df.to_csv(REPORTS_DIR / "outliers_iqr.csv", index=False)

    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 70)
    print("=== Referential integrity (13 relationships) ===")
    piv = ri_df.pivot_table(index="relationship", columns="stage", values=["match_rate", "orphan_rows"], aggfunc="first")
    print(piv.reindex(ri_df.relationship.unique()).to_string())

    print("\n=== Rules that fail in either stage ===")
    rp = rules_df.pivot_table(index=["table", "rule"], columns="stage", values="fail_rows", aggfunc="first")
    print(rp[(rp > 0).any(axis=1)][["raw", "clean"]].to_string())

    print("\n=== Reconciliations ===")
    print(rec_df.pivot_table(index="reconciliation", columns="stage", values="agree_pct", aggfunc="first")
          [["raw", "clean"]].to_string())

    print("\n=== IQR outliers ===")
    print(iqr_df[["stage", "table", "column", "upper_fence", "flagged", "flagged_pct", "max_value",
                  "flagged_client_tier_mix"]].to_string(index=False))
    print("Flagged does not mean wrong: an IQR fence only says a value is far from the middle of the distribution. "
          "Large UHNW balances and trades are real, so flagged rows are for review, not deletion.")

    print("\n=== Data quality scorecard ===")
    print(sc.to_string(index=False))

    # the clean stage must not be worse than raw on any dimension, and must be fully joinable
    for t in TABLES:
        r_, c_ = sc[(sc.table == t) & (sc.stage == "raw")].iloc[0], sc[(sc.table == t) & (sc.stage == "clean")].iloc[0]
        for m in ["pct_completeness", "pct_key_uniqueness", "pct_type_validity", "pct_rule_pass"]:
            assert c_[m] >= r_[m], f"{t} {m} got worse"
    assert (ri_df[ri_df.stage == "clean"].match_rate == 1.0).all(), "clean data still has orphans"
    print("\nAll clean-stage assertions passed: no metric got worse and every relationship matches 100%.")


if __name__ == "__main__":
    main()
