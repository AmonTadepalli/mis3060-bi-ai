"""HW6 Part C: pandas evidence for design questions (a)-(d), plus the Part D edge case.

Run from the repo root:  python hw06/scripts/02_design_questions.py
Writes reports/design_questions.txt
"""
from pathlib import Path

import pandas as pd

HW = Path(__file__).resolve().parents[1]
DATA = HW / "data" / "clean"
out = []


def say(line=""):
    print(line)
    out.append(line)


snap = pd.read_csv(DATA / "fact_portfolio_snapshot.csv", parse_dates=["snapshot_date"])
fees = pd.read_csv(DATA / "fact_fees.csv", parse_dates=["fee_date"])
txns = pd.read_csv(DATA / "fact_transactions.csv", parse_dates=["txn_date"])
clients = pd.read_csv(DATA / "dim_client.csv")
tier = clients.set_index("client_id")["client_tier"]
last = snap["snapshot_date"].max()

# (a) Ending AUM vs SUMX over clients of [Ending AUM]
say("(a) Ending AUM vs SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )")
ending = snap.loc[snap["snapshot_date"] == last, "aum"].sum()
per_client_last = snap.sort_values("snapshot_date").groupby("client_id").tail(1)
sumx = per_client_last["aum"].sum()
gone = per_client_last[per_client_last["snapshot_date"] < last]
say(f"  Ending AUM (one firm-wide last date {last.date()}): {ending:,.2f}")
say(f"  SUMX over clients (each client's own last date):  {sumx:,.2f}")
say(f"  Difference: {sumx - ending:,.2f} = final balances of {len(gone)} clients whose last snapshot "
    f"is before {last.date()} (sum {gone['aum'].sum():,.2f})")
say(f"  Those clients' last snapshots run from {gone['snapshot_date'].min().date()} "
    f"to {gone['snapshot_date'].max().date()}")
say(f"  Clients in dim_client with no snapshot at all: {len(set(clients.client_id) - set(snap.client_id))}")
say()

# (b) Fee Yield vs Effective Fee Rate, 2024
say("(b) 2024 Fee Yield (bps) vs Effective Fee Rate (bps)")
s24 = snap[snap["snapshot_date"].dt.year == 2024]
f24 = fees[fees["fee_date"].dt.year == 2024]
fy = f24["amount"].sum() * 12 * 1e4 / s24["aum"].sum()
efr = f24["amount"].sum() * 12 * 1e4 / f24["aum_basis"].sum()
say(f"  Total fees 2024: {f24['amount'].sum():,.2f}")
say(f"  Fee Yield = fees x 12 x 10,000 / sum(snapshot aum)   = {fy:.4f} bps  (denominator {s24['aum'].sum():,.2f})")
say(f"  Effective Fee Rate = ... / sum(fees aum_basis)       = {efr:.4f} bps  (denominator {f24['aum_basis'].sum():,.2f})")
m = s24.merge(f24[["client_id", "fee_date", "aum_basis"]], left_on=["client_id", "snapshot_date"],
              right_on=["client_id", "fee_date"], how="left")
billed = m["fee_date"].notna()
say(f"  Snapshot rows 2024: {len(m):,}; with a fee row: {billed.sum():,}; with NO fee row: {(~billed).sum():,}")
say(f"  AUM on unbilled client-months: {m.loc[~billed, 'aum'].sum():,.2f} "
    f"({m.loc[~billed, 'aum'].sum() / m['aum'].sum():.2%} of 2024 snapshot AUM)")
say(f"  aum_basis differs from snapshot aum on matched rows: {(m.loc[billed, 'aum_basis'] - m.loc[billed, 'aum']).abs().gt(0.01).sum()}")
say(f"  Fee Yield using only billed snapshot rows: "
    f"{f24['amount'].sum() * 12 * 1e4 / m.loc[billed, 'aum'].sum():.4f} bps (= Effective Fee Rate)")
unb = m.loc[~billed].assign(tier=lambda d: d.client_id.map(tier))
say("  Unbilled client-months by tier: " + ", ".join(f"{k} {v:,}" for k, v in unb.tier.value_counts().items()))
say(f"  Distinct clients with at least one unbilled 2024 month: {unb.client_id.nunique():,}")
all_m = snap.merge(fees[["client_id", "fee_date"]], left_on=["client_id", "snapshot_date"],
                   right_on=["client_id", "fee_date"], how="left")
say("  Unbilled snapshot rows by year: " + ", ".join(
    f"{y} {n:,}" for y, n in all_m[all_m.fee_date.isna()].snapshot_date.dt.year.value_counts().sort_index().items()))
say()

# (c) AUM-Weighted Alpha: last snapshot only, suspects excluded
say("(c) AUM-Weighted Alpha at the last snapshot")
ls = snap[snap["snapshot_date"] == last]
clean = ls[ls["is_return_suspect"] == 0]
w = lambda d: (d["aum"] * d["active_alpha_ytd"]).sum() / d["aum"].sum()
say(f"  Rows at {last.date()}: {len(ls):,}; suspect rows: {int(ls['is_return_suspect'].sum())}")
say(f"  Weighted, suspects excluded (the measure): {w(clean):.6f}")
say(f"  Simple mean, same rows (suspects excluded): {clean['active_alpha_ytd'].mean():.6f}")
say(f"  Weighted, suspects INCLUDED:                {w(ls):.6f}")
say(f"  Simple mean, suspects included:             {ls['active_alpha_ytd'].mean():.6f}")
sus = ls[ls["is_return_suspect"] == 1]
say(f"  Suspect rows' alpha: min {sus['active_alpha_ytd'].min():.4f}, median {sus['active_alpha_ytd'].median():.4f}, "
    f"max {sus['active_alpha_ytd'].max():.4f}; their AUM {sus['aum'].sum():,.2f}")
s24w = s24[s24["is_return_suspect"] == 0]
say(f"  Wrong: weighted over ALL 2024 months (YTD values from Jan..Dec mixed): {w(s24w):.6f}")
say()

# (d) Organic growth vs AUM YoY by tier, 2024
say("(d) 2024 by tier: organic growth vs AUM YoY")
end23 = snap[snap["snapshot_date"] == "2023-12-01"].assign(tier=lambda d: d.client_id.map(tier))
end24 = ls.assign(tier=lambda d: d.client_id.map(tier))
t24 = txns[txns["txn_date"].dt.year == 2024].assign(tier=lambda d: d.client_id.map(tier))
for tr in ["Retail", "HNW", "UHNW"]:
    a0 = end23.loc[end23.tier == tr, "aum"].sum()
    a1 = end24.loc[end24.tier == tr, "aum"].sum()
    dep = t24.loc[(t24.tier == tr) & (t24.txn_type == "Deposit"), "amount"].sum()
    wd = t24.loc[(t24.tier == tr) & (t24.txn_type == "Withdrawal"), "amount"].sum()
    nf = dep - wd
    say(f"  {tr:6s} AUM 2023-12 {a0:>16,.0f}  2024-12 {a1:>16,.0f}  change {a1 - a0:>14,.0f}  "
        f"net flows {nf:>13,.0f}  organic {nf / a0:7.2%}  YoY {(a1 - a0) / a0:7.2%}  "
        f"non-flow change {(a1 - a0 - nf):>14,.0f}")
c23 = set(end23.client_id); c24 = set(end24.client_id)
say(f"  Clients at 2023-12: {len(c23)}, at 2024-12: {len(c24)}, left: {len(c23 - c24)}, joined: {len(c24 - c23)}")
fee_txn = t24[t24.txn_type == "Advisory Fee"].groupby("tier")["amount"].sum()
say("  2024 'Advisory Fee' debits (not in Net Flows): " + ", ".join(f"{k} {v:,.0f}" for k, v in fee_txn.items()))
say()

# Part D edge case: ranking clients by [Ending AUM] (own last date) instead of AUM at the filter's last date
say("Part D edge case: Top 10 ranked by each client's own [Ending AUM]")
own = per_client_last.set_index("client_id")["aum"].nlargest(10)
at_last = ls.groupby("client_id")["aum"].sum()
say(f"  Clients in that top 10 with no snapshot on {last.date()}: {(~own.index.isin(at_last.index)).sum()}")
say(f"  Share if ranked by own last balance: {at_last.reindex(own.index).fillna(0).sum() / at_last.sum():.6f}; "
    f"ranked at last date: {at_last.nlargest(10).sum() / at_last.sum():.6f}")
for yr in [2022, 2023]:
    ys = snap[snap.snapshot_date.dt.year == yr]
    yl = ys[ys.snapshot_date == ys.snapshot_date.max()].groupby("client_id")["aum"].sum()
    yown = ys.sort_values("snapshot_date").groupby("client_id").tail(1).set_index("client_id")["aum"].nlargest(10)
    say(f"  {yr}: top-10 by own last balance includes {(~yown.index.isin(yl.index)).sum()} client(s) absent at "
        f"{ys.snapshot_date.max().date()}; correct share {yl.nlargest(10).sum() / yl.sum():.6f}, "
        f"own-balance version {yl.reindex(yown.index).fillna(0).sum() / yl.sum():.6f}")

(HW / "reports" / "design_questions.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
