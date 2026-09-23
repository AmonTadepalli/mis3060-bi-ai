"""
hw02_eda.py

Script:   HW2 Vibe Coding EDA
Dataset:  data/raw/fact_transactions.csv (Wildcat Capital transaction portfolio)
Author:   Amon Tadepalli
Generated: 2026-09-22

Performs a full exploratory data analysis pass on the Wildcat Capital
fact_transactions dataset: structural checks, missing-value counts,
descriptive statistics, distribution shape, grouping, correlation, and
anomaly detection. Saves three charts and a plain-text profile summary.
Running this file top to bottom produces every required output in a
single execution -- no manual steps in between.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_PATH = Path("data/raw/fact_transactions.csv")
CHARTS_DIR = Path("hw02/charts")
PROFILE_PATH = Path("hw02/hw02_profile.txt")
EXPECTED_SHAPE = (298772, 9)

CHARTS_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Buffer that collects everything printed for steps 2-13 so it can also be
# written to hw02/hw02_profile.txt (item 16).
profile_lines = []


def emit(text=""):
    """Print to the terminal and also capture the line for the profile file."""
    print(text)
    profile_lines.append(text)


def section(title):
    emit()
    emit("=" * 70)
    emit(title)
    emit("=" * 70)


# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------
print(f"Loading {DATA_PATH} ...")
df = pd.read_csv(DATA_PATH)
print("Load complete.\n")

# ---------------------------------------------------------------------------
# 2. Shape
# ---------------------------------------------------------------------------
section("2. DATASET SHAPE")
emit(f"Rows x Columns: {df.shape[0]:,} x {df.shape[1]}")

# ---------------------------------------------------------------------------
# 3. Schema (column names + dtypes)
# ---------------------------------------------------------------------------
section("3. COLUMN NAMES AND DATA TYPES")
for col, dtype in df.dtypes.items():
    emit(f"  {col:<15} {dtype}")

# ---------------------------------------------------------------------------
# 4. Missing values per column
# ---------------------------------------------------------------------------
section("4. MISSING VALUES PER COLUMN")
null_counts = df.isnull().sum()
for col, count in null_counts.items():
    emit(f"  {col:<15} {count:,}")

# ---------------------------------------------------------------------------
# 5. Descriptive statistics for numeric columns
# ---------------------------------------------------------------------------
section("5. DESCRIPTIVE STATISTICS (NUMERIC COLUMNS)")
numeric_df = df.select_dtypes(include=[np.number])
desc = numeric_df.describe().round(2)
emit(desc.to_string())

# ---------------------------------------------------------------------------
# 6. txn_type distribution (counts + percentages, most to least frequent)
# ---------------------------------------------------------------------------
section("6. TXN_TYPE DISTRIBUTION")
type_counts = df["txn_type"].value_counts()
type_pcts = df["txn_type"].value_counts(normalize=True) * 100
for txn_type in type_counts.index:
    emit(f"  {txn_type:<15} {type_counts[txn_type]:>8,}   ({type_pcts[txn_type]:5.2f}%)")

# ---------------------------------------------------------------------------
# 7. Unique entity counts
# ---------------------------------------------------------------------------
section("7. UNIQUE ENTITY COUNTS")
emit(f"  Unique clients:    {df['client_id'].nunique():,}")
emit(f"  Unique advisors:   {df['advisor_id'].nunique():,}")
emit(f"  Unique securities: {df['security_id'].nunique():,}")

# ---------------------------------------------------------------------------
# 8. Date range
# ---------------------------------------------------------------------------
section("8. DATE RANGE")
emit(f"  Earliest txn_date: {df['txn_date'].min()}")
emit(f"  Latest txn_date:   {df['txn_date'].max()}")

# ---------------------------------------------------------------------------
# 9. Duplicate txn_id check
# ---------------------------------------------------------------------------
section("9. DUPLICATE TXN_ID CHECK")
dup_count = df["txn_id"].duplicated().sum()
emit(f"  Duplicate txn_id count: {dup_count:,}")

# ---------------------------------------------------------------------------
# 10. amount shape statistics: mean, median, skewness
# ---------------------------------------------------------------------------
section("10. AMOUNT DISTRIBUTION SHAPE")
amount_mean = df["amount"].mean()
amount_median = df["amount"].median()
amount_skew = df["amount"].skew()
emit(f"  Mean amount:     ${amount_mean:,.2f}")
emit(f"  Median amount:   ${amount_median:,.2f}")
emit(f"  Skewness amount: {amount_skew:.2f}")

# ---------------------------------------------------------------------------
# 11. Group by txn_type: count, mean, median amount (sorted by mean desc)
# ---------------------------------------------------------------------------
section("11. GROUP SUMMARY BY TXN_TYPE (sorted by mean amount, descending)")
group_summary = (
    df.groupby("txn_type")["amount"]
    .agg(count="count", mean_amount="mean", median_amount="median")
    .round(2)
    .sort_values("mean_amount", ascending=False)
)
emit(group_summary.to_string())

# ---------------------------------------------------------------------------
# 12. Correlation matrix: shares, price, amount + three strongest pairs
# ---------------------------------------------------------------------------
section("12. CORRELATION MATRIX (shares, price, amount)")
corr_matrix = df[["shares", "price", "amount"]].corr().round(2)
emit(corr_matrix.to_string())

# Unstack to get each pair once, excluding self-correlations.
corr_pairs = (
    corr_matrix.where(~np.eye(len(corr_matrix), dtype=bool))
    .stack()
    .reset_index()
)
corr_pairs.columns = ["var_1", "var_2", "correlation"]
# Drop the mirrored duplicate of each pair (A-B and B-A).
corr_pairs["pair_key"] = corr_pairs.apply(
    lambda r: tuple(sorted([r["var_1"], r["var_2"]])), axis=1
)
corr_pairs = corr_pairs.drop_duplicates(subset="pair_key").drop(columns="pair_key")
corr_pairs["abs_correlation"] = corr_pairs["correlation"].abs()
corr_pairs = corr_pairs.sort_values("abs_correlation", ascending=False)

emit("\n  Three strongest correlations (excluding self-correlation):")
for _, row in corr_pairs.head(3).iterrows():
    emit(f"    {row['var_1']} - {row['var_2']}: {row['correlation']:.2f}")

# ---------------------------------------------------------------------------
# 13. shares by txn_type: min, max, count of negative values
# ---------------------------------------------------------------------------
section("13. SHARES BY TXN_TYPE (min, max, negative count)")
shares_by_type = df.groupby("txn_type")["shares"].agg(
    min_shares="min",
    max_shares="max",
    negative_count=lambda s: (s < 0).sum(),
)
emit(shares_by_type.to_string())

# ---------------------------------------------------------------------------
# 14. Shape validation warning
# ---------------------------------------------------------------------------
section("14. SHAPE VALIDATION")
if df.shape != EXPECTED_SHAPE:
    emit(
        f"  WARNING: expected shape {EXPECTED_SHAPE}, "
        f"but got {df.shape}. Investigate before proceeding."
    )
else:
    emit(f"  OK: shape matches expected {EXPECTED_SHAPE}.")

# ---------------------------------------------------------------------------
# 15. Charts
# ---------------------------------------------------------------------------
print("\nGenerating charts...")

# 15a. Histogram of amount with mean/median lines
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(df["amount"], bins=60, color="#4C72B0", edgecolor="white")
ax.axvline(amount_mean, color="#C44E52", linestyle="--", linewidth=2,
           label=f"Mean = ${amount_mean:,.2f}")
ax.axvline(amount_median, color="#55A868", linestyle="--", linewidth=2,
           label=f"Median = ${amount_median:,.2f}")
ax.set_title("Distribution of Transaction Amount")
ax.set_xlabel("Amount ($)")
ax.set_ylabel("Frequency")
ax.legend()
fig.tight_layout()
fig.savefig(CHARTS_DIR / "hist_amount.png", dpi=150)
plt.close(fig)

# 15b. Horizontal box plot of amount by txn_type
fig, ax = plt.subplots(figsize=(10, 6))
order = df.groupby("txn_type")["amount"].median().sort_values().index
data_by_type = [df.loc[df["txn_type"] == t, "amount"] for t in order]
ax.boxplot(data_by_type, vert=False, labels=order, showfliers=True)
ax.set_title("Amount by Transaction Type")
ax.set_xlabel("Amount ($)")
ax.set_ylabel("Transaction Type")
fig.tight_layout()
fig.savefig(CHARTS_DIR / "box_amount_by_type.png", dpi=150)
plt.close(fig)

# 15c. Scatter plot of shares vs. amount, colored by txn_type
fig, ax = plt.subplots(figsize=(10, 6))
categories = df["txn_type"].unique()
cmap = plt.get_cmap("tab10")
for i, cat in enumerate(categories):
    subset = df[df["txn_type"] == cat]
    ax.scatter(subset["shares"], subset["amount"], s=8, alpha=0.4,
               color=cmap(i % 10), label=cat)
ax.set_title("Shares vs. Amount by Transaction Type")
ax.set_xlabel("Shares")
ax.set_ylabel("Amount ($)")
ax.legend(markerscale=2, loc="upper right")
fig.tight_layout()
fig.savefig(CHARTS_DIR / "scatter_shares_amount.png", dpi=150)
plt.close(fig)

print(f"Charts saved to {CHARTS_DIR}/")

# ---------------------------------------------------------------------------
# 16. Save plain-text summary (steps 2-13) to hw02/hw02_profile.txt
# ---------------------------------------------------------------------------
with open(PROFILE_PATH, "w") as f:
    f.write("\n".join(profile_lines))
print(f"Profile summary saved to {PROFILE_PATH}")

print("\nDone.")
