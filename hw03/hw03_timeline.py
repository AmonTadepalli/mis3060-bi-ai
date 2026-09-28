"""
HW3 Part 4: Corporate Events Timeline
MIS3060 Business Intelligence with AI | Amon Tadepalli

Joins the executive events table (Item 5.02) to the earnings history table
(Item 2.02). Each executive event is matched to the nearest earnings filing
for the same company, and labeled by when it happened relative to earnings.

Run from the repo root:
    python hw03/hw03_timeline.py

Inputs:
    hw03/earnings_history.csv
    hw03/executive_events.csv

Output:
    hw03/corporate_events_timeline.csv
"""

import pandas as pd

# ---------------------------------------------------------------------------
# Step 0: Configuration
# ---------------------------------------------------------------------------

EARNINGS_CSV = "hw03/earnings_history.csv"
EVENTS_CSV = "hw03/executive_events.csv"
OUTPUT_CSV = "hw03/corporate_events_timeline.csv"

# An event within this many days of an earnings filing counts as 'same week'.
SAME_WEEK_DAYS = 7

# Columns both tables share. Keys used to join on company.
SHARED_COLUMNS = ["company", "ticker", "cik"]

# ---------------------------------------------------------------------------
# Step 1: Load both tables
# ---------------------------------------------------------------------------

# Read cik as text so leading zeros (e.g. 0000320193) are kept.
earnings = pd.read_csv(EARNINGS_CSV, dtype={"cik": str})
events = pd.read_csv(EVENTS_CSV, dtype={"cik": str})

earnings["filing_date"] = pd.to_datetime(earnings["filing_date"])
events["filing_date"] = pd.to_datetime(events["filing_date"])

# Both tables have a filing_date column. Rename the earnings one so the
# combined table keeps both dates side by side.
earnings = earnings.rename(columns={"filing_date": "earnings_filing_date"})
earnings_only_cols = [c for c in earnings.columns if c not in SHARED_COLUMNS]

# ---------------------------------------------------------------------------
# Step 2: Find the nearest earnings filing for each executive event
# ---------------------------------------------------------------------------

def classify(signed_days):
    """Label an event by its timing relative to the nearest earnings filing.

    signed_days = event filing_date - earnings filing_date
      negative -> event came before earnings
      positive -> event came after earnings
    'same week' takes priority when the gap is 7 days or less.
    """
    if abs(signed_days) <= SAME_WEEK_DAYS:
        return "same week"
    return "before earnings" if signed_days < 0 else "after earnings"


rows = []
for _, event in events.iterrows():
    company_earnings = earnings[earnings["cik"] == event["cik"]]

    if company_earnings.empty:
        # No earnings rows for this company: keep the event, leave match blank.
        match = {col: None for col in earnings_only_cols}
        match["days_to_nearest_earnings"] = None
        match["event_timing"] = None
    else:
        gaps = (event["filing_date"] - company_earnings["earnings_filing_date"]).dt.days
        # Nearest = smallest absolute gap. On a tie, idxmin keeps the first
        # (most recent) earnings row, since the table is sorted newest first.
        nearest_idx = gaps.abs().idxmin()
        signed_days = int(gaps.loc[nearest_idx])

        match = company_earnings.loc[nearest_idx, earnings_only_cols].to_dict()
        match["days_to_nearest_earnings"] = abs(signed_days)
        match["event_timing"] = classify(signed_days)

    rows.append({**event.to_dict(), **match})

timeline = pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# Step 3: Save the combined table
# ---------------------------------------------------------------------------

column_order = (
    list(events.columns)
    + earnings_only_cols
    + ["days_to_nearest_earnings", "event_timing"]
)
timeline = timeline[column_order].sort_values(["company", "filing_date"])

# Write dates back out as plain YYYY-MM-DD strings.
timeline["filing_date"] = timeline["filing_date"].dt.strftime("%Y-%m-%d")
timeline["earnings_filing_date"] = pd.to_datetime(
    timeline["earnings_filing_date"]
).dt.strftime("%Y-%m-%d")
timeline["days_to_nearest_earnings"] = timeline["days_to_nearest_earnings"].astype("Int64")

timeline.to_csv(OUTPUT_CSV, index=False)
print(f"Saved {len(timeline)} rows to {OUTPUT_CSV}\n")

# ---------------------------------------------------------------------------
# Step 4: Per-company summary
# ---------------------------------------------------------------------------

print("=" * 78)
print("EXECUTIVE EVENTS RELATIVE TO NEAREST EARNINGS ANNOUNCEMENT")
print("=" * 78)

for company, group in timeline.groupby("company", sort=True):
    ticker = group["ticker"].iloc[0]
    print(f"\n{company} ({ticker}) - {len(group)} event(s)")
    for _, row in group.iterrows():
        print(
            f"  {row['filing_date']}  {row['event_type']:<11} "
            f"{row['person_name']:<24} -> {row['event_timing']:<15} "
            f"({row['days_to_nearest_earnings']} days from "
            f"{row['earnings_filing_date']} earnings, {row['period']})"
        )

# ---------------------------------------------------------------------------
# Step 5: Final count across all companies
# ---------------------------------------------------------------------------

counts = timeline["event_timing"].value_counts()
n_companies = timeline["company"].nunique()

print("\n" + "=" * 78)
print(f"FINAL COUNT ACROSS ALL {n_companies} COMPANIES ({len(timeline)} events)")
print("=" * 78)
for label in ["before earnings", "after earnings", "same week"]:
    print(f"  {label:<16} {counts.get(label, 0)}")
print(
    "\nNote: 'same week' events (within 7 days of an earnings filing) are "
    "counted separately, not as before or after."
)

# Per-company breakdown for quick comparison.
print("\nBy company:")
print(
    pd.crosstab(timeline["ticker"], timeline["event_timing"])
    .reindex(columns=["before earnings", "after earnings", "same week"], fill_value=0)
    .to_string()
)
