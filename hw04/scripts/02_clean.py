"""
HW4 Part C: clean the Wildcat Capital extract.

Reads the 8 raw files (never modified) and writes 8 clean files with the same
names and columns, plus clearly named 0/1 flag columns where a value is
suspicious but cannot be corrected without inventing data.

Every step maps to an entry in decision_log.md. After each step the script
prints rows affected and a before/after check, then asserts the after-state;
if a fix did not do what it claims, the script stops.

Order (defended in decision_log.md):
  dimensions before facts, so fact RI checks run against final keys;
  inside a table: type conversion -> quarantine -> value fix -> flag.

Outputs:
  data/clean/<table>.csv                      8 clean tables
  data/audit/cleaning_log.csv                 one row per step
  data/audit/value_changes.csv                one row per changed cell
  data/audit/quarantine_<table>_<reason>.csv  removed rows, traceable

Usage:  python hw04/scripts/02_clean.py
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wildcat_schema import (AUDIT_DIR, CASH_TXN_TYPES, CLEAN_DIR, RAW_DIR, SCHEMA, SECURITY_TXN_TYPES,
                            TABLES, US_STATES, load_tables)

CLEANING_LOG, VALUE_CHANGES, QUARANTINE = [], [], {}


def num(s):
    return pd.to_numeric(s.where(s.str.strip() != ""), errors="coerce")


def header(step, decision, table, issue):
    print(f"\n[{step}] {decision} {table}: {issue}")


def log_step(step, decision, table, issue, action, rows, note=""):
    CLEANING_LOG.append({"step": step, "decision_id": decision, "table": table, "issue": issue,
                         "action": action, "rows_affected": int(rows), "note": note})
    print(f"    rows affected: {rows:,}  ({action})")


def log_changes(table, df, mask, column, new_values):
    """Record old -> new for every changed cell, then apply the change."""
    key = SCHEMA[table]["pk"]
    old = df.loc[mask, column]
    new = new_values.reindex(old.index) if isinstance(new_values, pd.Series) else pd.Series(new_values, index=old.index)
    assert new.notna().all(), f"{table}.{column}: a replacement value is missing"
    VALUE_CHANGES.append(pd.DataFrame({"table": table, "key_column": key, "key": df.loc[mask, key],
                                       "column": column, "old_value": old, "new_value": new}))
    df.loc[mask, column] = new
    return int(mask.sum())


def quarantine(table, df, mask, reason, decision, extra=None):
    """Move rows to a quarantine set with the reason attached. Returns the kept rows."""
    q = df[mask].copy()
    if extra is not None:
        q = q.join(extra)
    q["quarantine_reason"] = reason
    q["decision_id"] = decision
    QUARANTINE.setdefault(table, []).append(q)
    return df[~mask].copy()


def oversold_sells(x):
    """Sells whose running Buy-minus-Sell position per client-security goes negative."""
    tr = x[x.txn_type.isin(["Buy", "Sell"])].assign(q=num(x.shares).abs()).sort_values(["txn_date", "txn_id"])
    pos = (tr.q * np.where(tr.txn_type == "Buy", 1, -1)).groupby([tr.client_id, tr.security_id]).cumsum()
    return int(((tr.txn_type == "Sell") & (pos < -1e-6)).sum())


def fmt_decimal(x):
    """Write a decimal without scientific notation or trailing zeros (0.0928, -0.00005)."""
    s = f"{x:.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ==========================================================================
def main():
    raw = load_tables(RAW_DIR)
    T = {t: df.copy() for t, df in raw.items()}
    for t in TABLES:
        print(f"loaded {t:26s} {len(T[t]):>8,} rows x {T[t].shape[1]} cols")

    # ---------------------------------------------------------------- dim_client
    c = T["dim_client"]

    # C01 / D02: state names -> USPS codes (before de-dup: state is part of the near-dup match)
    header("C01", "D02", "dim_client", "state spelled out instead of 2-letter code")
    names = {"Pennsylvania": "PA", "Florida": "FL", "New York": "NY", "New Jersey": "NJ",
             "California": "CA", "Illinois": "IL", "Texas": "TX"}
    before_bad = ~c.state.isin(US_STATES)
    expected_counts = c.state.replace(names).value_counts()
    print(f"    before: {before_bad.sum()} invalid  {c.state[before_bad].value_counts().to_dict()}")
    assert set(c.state[before_bad]) <= set(names), f"unmapped state names: {set(c.state[before_bad]) - set(names)}"
    n = log_changes("dim_client", c, before_bad, "state", c.state[before_bad].map(names))
    after_bad = ~c.state.isin(US_STATES)
    print(f"    after:  {after_bad.sum()} invalid; PA now {(c.state == 'PA').sum()}")
    assert after_bad.sum() == 0
    assert c.state.value_counts().sort_index().equals(expected_counts.sort_index()), \
        "per-state counts changed beyond the mapping"
    log_step("C01", "D02", "dim_client", "state spelled out", "standardize", n,
             "7 full names mapped to USPS codes; per-state totals = code count + name count")

    # C02 / D01: near-duplicate clients -> quarantine the later copy
    header("C02", "D01", "dim_client", "near-duplicate clients (differ only in last_name)")
    cols = SCHEMA["dim_client"]["near_dup_cols"]
    c["_id"] = c.client_id.astype(int)
    c = c.sort_values("_id")
    dup = c.duplicated(cols, keep="first")
    first_ids = c[~dup].set_index(cols).client_id
    match = c[dup].join(first_ids.rename("kept_client_id"), on=cols)
    kept_last = match.kept_client_id.map(c.set_index("client_id").last_name)
    # verify: last names differ by exactly one character added or dropped at the end
    one_char = [(len(a) - len(b) == 1 and a.startswith(b)) or (len(b) - len(a) == 1 and b.startswith(a))
                for a, b in zip(kept_last, match.last_name)]
    fact_ids = set(T["fact_fees"].client_id) | set(T["fact_portfolio_snapshot"].client_id) | \
        set(T["fact_transactions"].client_id)
    print(f"    before: {len(c)} clients, {dup.sum()} later copies; e.g. "
          + ", ".join(f"{k}->{d} {l}/{m}" for d, k, l, m in
                      zip(match.client_id[:3], match.kept_client_id[:3], kept_last[:3], match.last_name[:3])))
    assert all(one_char), "a near-duplicate differs by more than one trailing letter: review manually"
    assert not set(match.client_id) & fact_ids, "a near-duplicate is referenced by a fact table"
    before_rows = len(c)
    c = quarantine("dim_client", c.drop(columns="_id"), dup, "near-duplicate of kept_client_id (last_name typo)",
                   "D01", extra=match[["kept_client_id"]].assign(kept_last_name=kept_last.values))
    print(f"    after:  {len(c)} clients; near-dups remaining {c.duplicated(cols).sum()}")
    assert len(c) == before_rows - dup.sum() and c.duplicated(cols).sum() == 0
    assert c.client_id.is_unique
    log_step("C02", "D01", "dim_client", "near-duplicate clients", "quarantine", dup.sum(),
             "all 25 differ from a kept client by one trailing letter of last_name; none referenced by any fact")
    T["dim_client"] = c

    # --------------------------------------------------------- fact_transactions
    x = T["fact_transactions"]

    # C03 / D09: security_id 45.0 -> 45
    header("C03", "D09", "fact_transactions", "security_id stored as decimal text")
    sec_keys = set(T["dim_security"].security_id)
    has = x.security_id != ""
    dotzero = x.security_id.str.match(r"^\d+\.0$")
    print(f"    before: {dotzero.sum():,} values like 45.0; RI match {x.security_id[has].isin(sec_keys).mean():.1%}")
    assert (dotzero == has).all(), "some security_id values have a nonzero decimal: not a pure format issue"
    n = log_changes("fact_transactions", x, dotzero, "security_id", x.security_id[dotzero].str[:-2])
    ri = x.security_id[has].isin(sec_keys).mean()
    print(f"    after:  RI match {ri:.1%}; blanks untouched {(x.security_id == '').sum():,}")
    assert x.security_id[has].str.match(r"^\d+$").all() and ri == 1.0
    log_step("C03", "D09", "fact_transactions", "security_id as decimal text", "convert", n,
             "dropped trailing .0; join to dim_security goes from 0% to 100%")

    # C04 / D10: transactions for clients missing from dim_client -> quarantine
    header("C04", "D10", "fact_transactions", "client_id not in dim_client")
    orphan = ~x.client_id.isin(set(T["dim_client"].client_id))
    orphan_amt = num(x.amount[orphan]).sum()
    print(f"    before: {orphan.sum()} orphan rows, {x.client_id[orphan].nunique()} distinct ids, ${orphan_amt:,.2f}")
    before_rows = len(x)
    x = quarantine("fact_transactions", x, orphan, "client_id not in dim_client", "D10")
    print(f"    after:  {len(x):,} rows; orphans remaining {(~x.client_id.isin(set(T['dim_client'].client_id))).sum()}")
    assert len(x) == before_rows - orphan.sum()
    assert x.client_id.isin(set(T["dim_client"].client_id)).all()
    log_step("C04", "D10", "fact_transactions", "orphan client_id", "quarantine", orphan.sum(),
             f"{orphan.sum()} rows / {raw['fact_transactions'].client_id[orphan].nunique()} distinct ids; "
             f"quarantined amount ${orphan_amt:,.2f}")

    # C05 / D11: negative shares on Buys -> absolute value, reconciled to amount
    header("C05", "D11", "fact_transactions", "negative shares on Buy")
    sh, px, amt = num(x.shares), num(x.price), num(x.amount)
    neg = (x.txn_type == "Buy") & (sh < 0)
    proves = ((amt[neg] - (sh[neg].abs() * px[neg]).round(2)).abs() <= 0.011).all()
    sec_rows = x.txn_type.isin(SECURITY_TXN_TYPES)
    recon_before = ((amt - (sh * px).round(2)).abs() <= 0.011)[sec_rows].mean()
    print(f"    before: {neg.sum()} negative Buys; amount = shares x price on {recon_before:.2%} of security txns")
    assert proves, "amount does not equal |shares| x price for every negative Buy: sign fix not proven"
    assert not ((x.txn_type != "Buy") & (sh < 0)).any(), "negative shares outside Buy: not covered by D11"
    n = log_changes("fact_transactions", x, neg, "shares", x.shares[neg].str.lstrip("-"))
    sh = num(x.shares)
    recon_after = ((amt - (sh * px).round(2)).abs() <= 0.011)[sec_rows].mean()
    print(f"    after:  negative shares {(sh < 0).sum()}; amount = shares x price on {recon_after:.2%}")
    assert (sh < 0).sum() == 0 and recon_after == 1.0
    log_step("C05", "D11", "fact_transactions", "negative shares on Buy", "convert", n,
             "sign removed; amount = shares x price now holds on 100% of Buy/Sell/Dividend rows")

    # C06 / D13: Buy/Sell on a non-trading day -> flag
    header("C06", "D13", "fact_transactions", "Buy/Sell dated on a non-trading day")
    trading = x.txn_date.map(T["dim_date"].set_index("date").is_trading_day)
    assert trading.notna().all(), "txn_date missing from dim_date"
    mask = x.txn_type.isin(["Buy", "Sell"]) & (trading == "0")
    x["non_trading_day_flag"] = np.where(mask, "1", "0")
    print(f"    after:  flagged {mask.sum():,} of {x.txn_type.isin(['Buy', 'Sell']).sum():,} trades")
    assert (x.non_trading_day_flag == "1").sum() == mask.sum()
    assert not ((x.non_trading_day_flag == "1") & ~x.txn_type.isin(["Buy", "Sell"])).any()
    log_step("C06", "D13", "fact_transactions", "trade on non-trading day", "flag", mask.sum(),
             "non_trading_day_flag = 1; date not changed (true trade date unknown)")

    # C07 / D14: activity after the client's last snapshot month -> flag
    header("C07", "D14", "fact_transactions", "txn after the client's last snapshot month")
    last = T["fact_portfolio_snapshot"].groupby("client_id").snapshot_date.max().str[:7]
    mask = x.txn_date.str[:7] > x.client_id.map(last)
    active = x.client_id.map(T["dim_client"].set_index("client_id").is_active)
    x["after_last_snapshot_flag"] = np.where(mask, "1", "0")
    print(f"    after:  flagged {mask.sum():,}; is_active of flagged clients {active[mask].value_counts().to_dict()}")
    assert (x.after_last_snapshot_flag == "1").sum() == mask.sum()
    assert (active[mask] == "False").all(), "an active client was flagged: re-check D14"
    log_step("C07", "D14", "fact_transactions", "txn after last snapshot", "flag", mask.sum(),
             "after_last_snapshot_flag = 1; all flagged rows belong to inactive clients")
    T["fact_transactions"] = x

    # --------------------------------------------------- fact_portfolio_snapshot
    p = T["fact_portfolio_snapshot"]

    # C08 / D17: return_ytd '9.28%' -> 0.0928, reconciled to alpha + benchmark
    header("C08", "D17", "fact_portfolio_snapshot", "return_ytd stored as percent text")
    pct = p.return_ytd.str.endswith("%")
    converted = num(p.return_ytd[pct].str.rstrip("%")) / 100
    implied = num(p.active_alpha_ytd[pct]) + num(p.benchmark_return_ytd[pct])
    gap = (converted - implied).abs()
    print(f"    before: {pct.sum()} percent values; e.g. {p.return_ytd[pct].iloc[0]} vs alpha+bench "
          f"{implied.iloc[0]:.6f}; max gap after /100 = {gap.max():.6f}")
    assert gap.max() <= 0.00006, "a converted return does not reconcile to alpha + benchmark"
    n = log_changes("fact_portfolio_snapshot", p, pct, "return_ytd", converted.map(fmt_decimal))
    r = num(p.return_ytd)
    print(f"    after:  non-numeric return_ytd {r.isna().sum()}; range {r.min():.4f} to {r.max():.4f}")
    assert r.notna().all()
    log_step("C08", "D17", "fact_portfolio_snapshot", "return_ytd as percent text", "convert", n,
             f"stripped % and divided by 100; every value within {gap.max():.6f} of alpha + benchmark")

    # C09 / D19: AUM stuck at the 1,000.00 floor -> flag
    header("C09", "D19", "fact_portfolio_snapshot", "aum exactly 1,000.00 (system floor)")
    mask = num(p.aum) == 1000
    p["aum_floor_flag"] = np.where(mask, "1", "0")
    print(f"    after:  flagged {mask.sum()} snapshots across {p.client_id[mask].nunique()} clients")
    assert (p.aum_floor_flag == "1").sum() == mask.sum() and (num(p.aum[p.aum_floor_flag == "1"]) == 1000).all()
    log_step("C09", "D19", "fact_portfolio_snapshot", "aum at 1,000.00 floor", "flag", mask.sum(),
             "aum_floor_flag = 1; value kept (true balance unknown)")
    T["fact_portfolio_snapshot"] = p

    # ---------------------------------------------- decisions to leave as is
    # logged with live counts so the audit trail covers every decision
    print("\n[leave as is] logging decisions with no data change")
    c, s, x, p, f = (T["dim_client"], T["dim_security"], T["fact_transactions"],
                     T["fact_portfolio_snapshot"], T["fact_fees"])
    adv_rows = x.txn_type == "Advisory Fee"
    for d, t, issue, rows, note in [
        ("D03", "dim_client", "blank risk_profile", (c.risk_profile == "").sum(),
         "not inferred from benchmark 3 (looks like a default)"),
        ("D04", "dim_client", "zip_code leading zeros", c.zip_code.str.startswith("0").sum(), "kept as text"),
        ("D05", "dim_advisor", "certifications = 'None'", (T["dim_advisor"].certifications == "None").sum(),
         "real value: no certification"),
        ("D06", "dim_security", "blank sector (ETFs) / expense ratio (stocks)",
         (s.sector == "").sum() + (s.expense_ratio_bps == "").sum(), "structural, split exactly by is_etf"),
        ("D07", "dim_security", "duplicate security names", s.name.duplicated(keep=False).sum(),
         "different tickers; ticker is the identifier"),
        ("D08", "dim_date", "is_trading_day ignores market holidays (weekday Christmases shown)",
         ((T["dim_date"].date.str[5:] == "12-25") & (T["dim_date"].is_trading_day == "1")).sum(),
         "simplified calendar; limitation"),
        ("D12", "fact_transactions", "blank security/shares/price on cash txns",
         (x.txn_type.isin(CASH_TXN_TYPES) & (x.security_id == "")).sum(), "structural"),
        ("D15", "fact_transactions", "Advisory Fee txns do not match fact_fees", adv_rows.sum(),
         "use fact_fees for fee revenue"),
        ("D16", "fact_transactions", "Sells exceed position from earlier Buys", oversold_sells(x),
         "no opening holdings in extract; positions cannot be rebuilt"),
        ("D18", "fact_portfolio_snapshot", "scientific notation in returns",
         (p.return_ytd.str.contains("e") | p.active_alpha_ytd.str.contains("e")).sum(), "valid numbers"),
        ("D20", "fact_portfolio_snapshot", "|return_ytd| > 100%", (num(p.return_ytd).abs() > 1).sum(),
         "internally consistent; IQR flag in Part D"),
        ("D21", "fact_portfolio_snapshot", "snapshot month with no fee row",
         (~p.set_index(["client_id", "snapshot_date"]).index.isin(
             f.set_index(["client_id", "fee_date"]).index)).sum(), "no evidence of missing fees"),
    ]:
        print(f"  {d} {t}: {issue}")
        log_step("--", d, t, issue, "leave as is", rows, note)

    # ------------------------------------------------------- final reconciliation
    print("\n[final] raw rows = clean rows + quarantined rows")
    qframes = {t: pd.concat(v) for t, v in QUARANTINE.items()}
    flags = {"fact_transactions": ["non_trading_day_flag", "after_last_snapshot_flag"],
             "fact_portfolio_snapshot": ["aum_floor_flag"]}
    for t in TABLES:
        nq = len(qframes.get(t, []))
        ok = len(raw[t]) == len(T[t]) + nq
        print(f"    {t:26s} raw {len(raw[t]):>8,} = clean {len(T[t]):>8,} + quarantined {nq:>4}  {'OK' if ok else 'FAIL'}")
        assert ok, f"{t}: rows lost or created"
        assert list(T[t].columns) == list(raw[t].columns) + flags.get(t, []), f"{t}: columns changed"
        keys = set(T[t][SCHEMA[t]['pk']]) | set(qframes[t][SCHEMA[t]['pk']]) if t in qframes \
            else set(T[t][SCHEMA[t]['pk']])
        assert keys == set(raw[t][SCHEMA[t]["pk"]]), f"{t}: a key was lost"

    # ------------------------------------------------------------------ write
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    for t in TABLES:
        T[t].to_csv(CLEAN_DIR / f"{t}.csv", index=False)
    pd.DataFrame(CLEANING_LOG).to_csv(AUDIT_DIR / "cleaning_log.csv", index=False)
    vc = pd.concat(VALUE_CHANGES, ignore_index=True)
    vc.to_csv(AUDIT_DIR / "value_changes.csv", index=False)
    names = {"dim_client": "quarantine_dim_client_near_duplicates.csv",
             "fact_transactions": "quarantine_fact_transactions_orphan_client.csv"}
    for t, q in qframes.items():
        q.to_csv(AUDIT_DIR / names[t], index=False)

    # re-read the written files as text to prove what landed on disk
    for t in TABLES:
        back = pd.read_csv(CLEAN_DIR / f"{t}.csv", dtype=str, keep_default_na=False)
        assert back.equals(T[t].reset_index(drop=True)), f"{t}: file on disk differs from cleaned frame"

    tot_raw, tot_clean = sum(len(raw[t]) for t in TABLES), sum(len(T[t]) for t in TABLES)
    tot_q = sum(len(q) for q in qframes.values())
    assert tot_raw == tot_clean + tot_q
    print(f"    TOTAL raw {tot_raw:,} = clean {tot_clean:,} + quarantined {tot_q} ({tot_q / tot_raw:.2%} of rows)")
    all_amt = num(raw["fact_transactions"].amount).sum()
    print(f"    quarantined transactions = {orphan_amt / all_amt:.3%} of ${all_amt:,.2f} raw transaction dollars")
    print("\nwrote 8 clean tables to data/clean/")
    print(f"cleaning_log.csv: {len(CLEANING_LOG)} rows | value_changes.csv: {len(vc):,} rows "
          f"{vc.groupby(['table', 'column']).size().to_dict()}")
    print("quarantine: " + ", ".join(f"{names[t]} ({len(q)})" for t, q in qframes.items()))


if __name__ == "__main__":
    main()
