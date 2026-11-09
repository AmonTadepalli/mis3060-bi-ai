"""HW6 Part B: reconcile every Power BI measure to an independent pandas calculation.

Reads only the clean CSVs for the pandas side. Power BI numbers come from
reports/powerbi_values.csv (columns: measure, slice, value), exported from DAX query view.

Writes:
  reports/pandas_values.csv           every pandas value (written even before Power BI values exist)
  reports/measure_reconciliation.csv  measure, slice, powerbi_value, pandas_value, abs_diff, match

Slice labels:  "Total" | "<year>" (e.g. "2023") | "2024 | <tier>" | "2024-12"
Run from the repo root:  python hw06/scripts/01_reconcile_measures.py   (exits 1 on any mismatch)
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

HW = Path(__file__).resolve().parents[1]
DATA = HW / "data" / "clean"
REPORTS = HW / "reports"

# ── Load (pandas side never touches Power BI output) ────────────────────────
snap = pd.read_csv(DATA / "fact_portfolio_snapshot.csv", parse_dates=["snapshot_date"])
fees = pd.read_csv(DATA / "fact_fees.csv", parse_dates=["fee_date"])
txns = pd.read_csv(DATA / "fact_transactions.csv", parse_dates=["txn_date"])
clients = pd.read_csv(DATA / "dim_client.csv")
dates = pd.read_csv(DATA / "dim_date.csv", parse_dates=["date"])

tier_of = clients.set_index("client_id")["client_tier"]
for df in (snap, fees, txns):
    df["client_tier"] = df["client_id"].map(tier_of)

DATE_MIN, DATE_MAX = dates["date"].min(), dates["date"].max()  # dim_date span: the "no filter" range

# Measure kinds decide the tolerance: currency 0.01, ratio/bps 0.0001, count exact, text equal
KIND = {
    "AUM (naive SUM)": "currency", "Ending AUM": "currency", "Ending Clients": "count",
    "Avg AUM per Client": "currency", "Ending AUM LY": "currency", "AUM YoY %": "ratio",
    "Ending AUM PM": "currency", "AUM MoM %": "ratio", "Avg Monthly AUM": "currency",
    "Fee Yield (bps)": "ratio", "Organic Growth Rate": "ratio", "AUM-Weighted Alpha": "ratio",
    "Alpha Signal": "text", "Top 10 Client Share": "ratio",
}
TOL = {"currency": 0.01, "ratio": 0.0001, "count": 0.0}


# ── A filter context = a date window plus an optional client tier ───────────
class Ctx:
    def __init__(self, start, end, tier=None):
        self.start, self.end, self.tier = pd.Timestamp(start), pd.Timestamp(end), tier

    def rows(self, df, date_col):
        m = df[date_col].between(self.start, self.end)
        if self.tier is not None:
            m &= df["client_tier"] == self.tier
        return df[m]

    def shift(self, years=0, months=0):
        """Mimic DATEADD / SAMEPERIODLASTYEAR: shift the window, keep only dates that exist in dim_date."""
        off = pd.DateOffset(years=years, months=months)
        start = max(self.start + off, DATE_MIN)
        end = min(self.end + off, DATE_MAX)  # an end before DATE_MIN gives an empty window
        if months:  # a whole-month window stays whole-month (Nov 30, not Nov 31)
            end = (end + pd.offsets.MonthEnd(0)) if self.end.is_month_end else end
        return Ctx(start, end, self.tier)


def last_snapshot(ctx):
    """LASTNONBLANK(dim_date[date], COUNTROWS(fact_portfolio_snapshot)): rows on the last date with data."""
    s = ctx.rows(snap, "snapshot_date")
    if s.empty:
        return s
    return s[s["snapshot_date"] == s["snapshot_date"].max()]


def blank_div(n, d):
    """DIVIDE(n, d): blank (NaN) when the denominator is blank or 0."""
    if d is None or pd.isna(d) or d == 0 or pd.isna(n):
        return np.nan
    return n / d


# ── Measures (numbering follows the brief) ─────────────────────────────────
def naive_sum(ctx):                                  # 0  the trap
    s = ctx.rows(snap, "snapshot_date")
    return s["aum"].sum() if len(s) else np.nan


def ending_aum(ctx):                                 # 1  last balance
    s = last_snapshot(ctx)
    return s["aum"].sum() if len(s) else np.nan


def ending_clients(ctx):                             # 2
    s = last_snapshot(ctx)
    return float(s["client_id"].nunique()) if len(s) else np.nan


def avg_aum_per_client(ctx):                         # 3
    return blank_div(ending_aum(ctx), ending_clients(ctx))


def ending_aum_ly(ctx):                              # 4
    return ending_aum(ctx.shift(years=-1))


def aum_yoy(ctx):
    ly = ending_aum_ly(ctx)
    return blank_div(ending_aum(ctx) - ly, ly)


def ending_aum_pm(ctx):                              # 5
    return ending_aum(ctx.shift(months=-1))


def aum_mom(ctx):
    pm = ending_aum_pm(ctx)
    return blank_div(ending_aum(ctx) - pm, pm)


def avg_monthly_aum(ctx):                            # 6
    s = ctx.rows(snap, "snapshot_date")
    return blank_div(s["aum"].sum(), s["snapshot_date"].nunique()) if len(s) else np.nan


def total_fees(ctx):
    f = ctx.rows(fees, "fee_date")
    return f["amount"].sum() if len(f) else np.nan


def fee_yield_bps(ctx):                              # 7  two fact tables
    s = ctx.rows(snap, "snapshot_date")
    return blank_div(total_fees(ctx) * 12 * 10_000, s["aum"].sum() if len(s) else np.nan)


def net_flows(ctx):
    t = ctx.rows(txns, "txn_date")
    dep = t.loc[t["txn_type"] == "Deposit", "amount"].sum()
    wd = t.loc[t["txn_type"] == "Withdrawal", "amount"].sum()
    return dep - wd if len(t) else np.nan


def organic_growth(ctx):                             # 8
    return blank_div(net_flows(ctx), ending_aum_ly(ctx))


def weighted_alpha(ctx):                             # 9  last date first, then drop suspects
    s = last_snapshot(ctx)
    s = s[s["is_return_suspect"] == 0]
    return blank_div((s["aum"] * s["active_alpha_ytd"]).sum(), s["aum"].sum()) if len(s) else np.nan


def alpha_signal(ctx):                               # 10
    a = weighted_alpha(ctx)
    if pd.isna(a):
        return ""
    return "Outperforming" if a >= 0.02 else "Lagging" if a <= -0.02 else "In line"


def top10_share(ctx):                                # 11  top 10 clients at the last snapshot in the filter
    s = last_snapshot(ctx)
    if s.empty:
        return np.nan
    by_client = s.groupby("client_id")["aum"].sum().sort_values(ascending=False)
    # DAX TOPN keeps every client tied at rank 10; nlargest would silently drop them
    top = by_client[by_client >= by_client.iloc[min(9, len(by_client) - 1)]]
    return blank_div(top.sum(), by_client.sum())


MEASURES = {
    "AUM (naive SUM)": naive_sum, "Ending AUM": ending_aum, "Ending Clients": ending_clients,
    "Avg AUM per Client": avg_aum_per_client, "Ending AUM LY": ending_aum_ly, "AUM YoY %": aum_yoy,
    "Ending AUM PM": ending_aum_pm, "AUM MoM %": aum_mom, "Avg Monthly AUM": avg_monthly_aum,
    "Fee Yield (bps)": fee_yield_bps, "Organic Growth Rate": organic_growth,
    "AUM-Weighted Alpha": weighted_alpha, "Alpha Signal": alpha_signal,
    "Top 10 Client Share": top10_share,
}

# ── Required slices ─────────────────────────────────────────────────────────
BY_YEAR = ["AUM (naive SUM)", "Ending AUM", "Ending AUM LY", "AUM YoY %", "Avg Monthly AUM",
           "Fee Yield (bps)", "Organic Growth Rate", "AUM-Weighted Alpha", "Alpha Signal"]
BY_TIER = ["Ending AUM", "Ending Clients", "Avg AUM per Client", "Ending AUM LY", "AUM YoY %",
           "Fee Yield (bps)", "Organic Growth Rate", "AUM-Weighted Alpha", "Alpha Signal",
           "Top 10 Client Share"]
DEC_2024 = ["Ending AUM", "Ending AUM PM", "AUM MoM %"]

plan = [(m, "Total", Ctx(DATE_MIN, DATE_MAX)) for m in MEASURES]
for y in sorted(dates["year"].unique()):
    plan += [(m, str(y), Ctx(f"{y}-01-01", f"{y}-12-31")) for m in BY_YEAR]
for tier in sorted(clients["client_tier"].dropna().unique()):  # from the data, not hard-coded
    plan += [(m, f"2024 | {tier}", Ctx("2024-01-01", "2024-12-31", tier)) for m in BY_TIER]
plan += [(m, "2024-12", Ctx("2024-12-01", "2024-12-31")) for m in DEC_2024]

pandas_vals = pd.DataFrame(
    [{"measure": m, "slice": sl, "pandas_value": MEASURES[m](ctx)} for m, sl, ctx in plan]
)
REPORTS.mkdir(exist_ok=True)
pandas_vals.to_csv(REPORTS / "pandas_values.csv", index=False)
print(f"pandas: {len(pandas_vals)} values -> reports/pandas_values.csv")

# ── Compare with Power BI ───────────────────────────────────────────────────
pbi_path = REPORTS / "powerbi_values.csv"
if not pbi_path.exists():
    sys.exit("reports/powerbi_values.csv not found: export it from DAX query view, then re-run.")

# sep=None sniffs comma vs tab, so a grid pasted straight from DAX query view also works
pbi = pd.read_csv(pbi_path, sep=None, engine="python", dtype=str, keep_default_na=False)
pbi.columns = [c.strip().strip("[]").lower() for c in pbi.columns]  # DAX headers come as [measure]
pbi["measure"] = pbi["measure"].str.strip()
pbi["slice"] = pbi["slice"].str.strip()

rec = pandas_vals.merge(pbi.rename(columns={"value": "powerbi_value"}),
                        on=["measure", "slice"], how="outer", indicator=True)


def compare(row):
    kind = KIND.get(row["measure"], "ratio")
    pv, dv = row["powerbi_value"], row["pandas_value"]
    if row["_merge"] != "both":
        return pd.Series({"abs_diff": np.nan, "match": False})
    if kind == "text":
        pv = "" if pd.isna(pv) else str(pv).strip()
        return pd.Series({"abs_diff": np.nan, "match": pv == (dv or "")})
    pv_num = pd.to_numeric(pv, errors="coerce") if str(pv).strip() else np.nan  # "" = BLANK()
    if pd.isna(pv_num) and pd.isna(dv):          # both blank (e.g. 2020 YoY): a match
        return pd.Series({"abs_diff": 0.0, "match": True})
    if pd.isna(pv_num) or pd.isna(dv):
        return pd.Series({"abs_diff": np.nan, "match": False})
    diff = abs(pv_num - dv)
    return pd.Series({"abs_diff": diff, "match": diff <= TOL[kind] + 1e-9})


rec[["abs_diff", "match"]] = rec.apply(compare, axis=1)
missing = rec[rec["_merge"] != "both"]
rec = rec[["measure", "slice", "powerbi_value", "pandas_value", "abs_diff", "match"]]
rec.to_csv(REPORTS / "measure_reconciliation.csv", index=False)

n_bad = int((~rec["match"]).sum())
print(f"reconciliation: {len(rec)} rows, {len(rec) - n_bad} match, {n_bad} mismatch "
      f"-> reports/measure_reconciliation.csv")
if len(missing):
    print("rows present on only one side:")
    print(missing[["measure", "slice", "_merge"]].to_string(index=False))
if n_bad:
    print(rec[~rec["match"]].to_string(index=False))
sys.exit(1 if n_bad else 0)
