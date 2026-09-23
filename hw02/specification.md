# EDA Script Specification

## Purpose

This document specifies the requirements for a single Python script that performs exploratory data analysis (EDA) on the transaction fact table used in this project. The script must be self-contained: running it once, top to bottom, produces every required console output, saved chart, and saved summary file with no manual steps in between.

## Deliverable

- **One Python script**, e.g. `hw02/hw02_eda.py`, that executes all steps below in a single run.
- Outputs written by the script:
  - `hw02/charts/hist_amount.png`
  - `hw02/charts/box_amount_by_type.png`
  - `hw02/charts/scatter_shares_amount.png`
  - `hw02/hw02_profile.txt`

## Input

- Source file: `data/raw/fact_transactions.csv`
- Loaded into a single pandas DataFrame at the start of the script.
- Columns: `txn_id`, `client_id`, `advisor_id`, `security_id`, `txn_date`, `txn_type`, `shares`, `price`, `amount`.

## Requirements

The script must perform the following steps, in order, in a single run:

1. **Load data.** Read `data/raw/fact_transactions.csv` into a pandas DataFrame.
2. **Shape.** Print the DataFrame's shape as rows x columns.
3. **Schema.** Print every column name alongside its data type.
4. **Missing values.** Print the count of missing (null) values for every column.
5. **Descriptive statistics.** For all numeric columns, print count, mean, std, min, 25th percentile, median, 75th percentile, and max.
6. **`txn_type` distribution.** Print value counts and percentages for `txn_type`, sorted from most to least frequent.
7. **Unique entity counts.** Print the number of unique clients, unique advisors, and unique securities referenced in the file.
8. **Date range.** Print the earliest and latest `txn_date` in the dataset.
9. **Duplicate check.** Check for duplicate rows by `txn_id` and print the duplicate count.
10. **`amount` shape statistics.** Print the mean, median, and skewness of the `amount` column.
11. **Group summary by `txn_type`.** Group by `txn_type` and print, for each type: the row count, and the mean and median `amount` (each rounded to 2 decimal places), sorted by mean amount descending.
12. **Correlation matrix.** Compute the correlation matrix for `shares`, `price`, and `amount` (rounded to 2 decimal places), print it, and identify the three strongest correlations, excluding a variable's correlation with itself.
13. **`shares` by `txn_type`.** For the `shares` column, broken out by `txn_type`, print the minimum, maximum, and count of negative values.
14. **Shape validation.** Print a warning if the DataFrame's shape is not `(298772, 9)`.
15. **Charts.** Create and save three charts to `hw02/charts/`:
    - A histogram of `amount`, with vertical lines marking the mean and median, each clearly labeled. Save as `hw02/charts/hist_amount.png`.
    - A horizontal box plot of `amount` grouped by `txn_type`. Save as `hw02/charts/box_amount_by_type.png`.
    - A scatter plot of `shares` (x-axis) vs. `amount` (y-axis), colored by `txn_type`. Save as `hw02/charts/scatter_shares_amount.png`.
16. **Text summary.** Save a plain-text summary covering the output of steps 2-13 to `hw02/hw02_profile.txt`.
17. **Header comment block.** Include a comment block at the top of the script identifying the script name, the dataset it analyzes, the author, and the date it was generated.

## Notes

- All console output should be clearly labeled (e.g. a printed heading before each section) so the terminal output is readable top to bottom.
- Rounding requirements (2 decimal places for group means/medians and the correlation matrix) must be applied to the printed and saved values, not just displayed incidentally.
- The script should run without errors on a fresh clone of this project, assuming `data/raw/fact_transactions.csv` is present and the packages in `requirements.txt` are installed.
