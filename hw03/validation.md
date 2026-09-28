# HW3 Validation

## 5A: Known-Answer Check (Earnings)

Company and quarter: Apple, third quarter fiscal 2026 (quarter ended June 27, 2026; filed 2026-07-30).

| Check | Official Source | Your CSV | Match? |
|---|---|---|---|
| Apple Q3 FY2026 Revenue | $109.4 billion ([Apple Newsroom, July 30, 2026](https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/)) | $109.4 billion | Yes |
| Apple Q3 FY2026 EPS Diluted | $2.02 ([Apple Newsroom, July 30, 2026](https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/)) | $2.02 | Yes |

Both values matched on the first run, so no regex fix was needed for this check.

## 5B: Known-Answer Check (Executive Events)

Event checked: Apple, filed 2026-04-20, John Ternus appointed Chief Executive Officer and Director.

| Check | News Source Confirms? | Notes |
|---|---|---|
| Person name and title | Yes | Apple's announcement names John Ternus as CEO and says he joins the board of directors. The CSV title "Chief Executive Officer and Director" matches. |
| Event type (departure/appointment) | Yes | Appointment. The same filing also produced rows for Tim Cook (CEO to Executive Chairman) and Art Levinson (Chair to Lead Independent Director), both tagged "both". |
| Effective date | Yes | September 1, 2026 in both the CSV and the announcement. |

Source: [Apple Newsroom, April 20, 2026](https://www.apple.com/newsroom/2026/04/tim-cook-to-become-apple-executive-chairman-john-ternus-to-become-apple-ceo/)

## 5C: Cross-Validation via Yahoo Finance

Script: `hw03/hw03_yfinance_check.py` (pulls AAPL quarterly revenue and net income with yfinance).

| Metric | From 8-K text extraction | From yfinance | Match? |
|---|---|---|---|
| Revenue | $109.4 billion | $109.4 billion | Yes |
| Net Income | $29,789 million | $29,789 million | Yes |

Notes: Both sources match exactly. The only difference is the period label: yfinance lists the quarter as ending 2026-06-30 (calendar quarter-end), while Apple's fiscal quarter actually ended June 27, 2026 and the 8-K calls it "third quarter fiscal 2026". Same quarter, different labeling convention. The other three quarters yfinance returned also match the CSV exactly ($111.2B / $29,578M, $143.8B / $42,097M, $102.5B / $27,466M).

## 5D: Pipeline Integrity Checks

| Check | Expected | Actual | Pass/Fail |
|---|---|---|---|
| `earnings_history.csv` row count | Up to 20 (5 companies x 4 quarters) | 20 | Pass |
| `executive_events.csv` row count | At least 0 (document actual) | 30 | Pass |
| `corporate_events_timeline.csv` created | Yes | Yes (30 rows) | Pass |
| Rows with all three fields `"NOT_FOUND"` | 0 (investigate if > 0) | 0 | Pass |

Additional notes:

- The "No executive events in past 12 months" message never printed because all five companies had at least one Item 5.02 filing. The check exists in `hw03_executives.py` (line 645).
- Two executive events have `NOT_FOUND` for `effective_date` (Chris Kondo at Apple and Marianne Lake at JPMorgan). The script could not find a date pattern for those departures and stored `NOT_FOUND` instead of leaving the cell blank, as the spec requires.
- Walmart's 2026-01-16 filing produced three appointments with the same title ("Executive Vice President, President and Chief Executive Officer"). The segment names were not captured, which is a limitation of the title extraction.
