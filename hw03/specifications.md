# HW3 Specifications
MIS3060 Business Intelligence with AI | Amon Tadepalli

These two specifications were written before any code was generated. Each one is meant to be pasted into Claude Cowork as a complete instruction.

---

## Specification A: Earnings Pipeline (Item 2.02)

Write a Python script saved as `hw03/hw03_earnings.py` that builds a quarterly earnings history for five companies from SEC 8-K earnings press releases. Use only `requests`, `beautifulsoup4`, and the Python standard library (`re`, `csv`, `time`, `json`).

**Companies (use these CIKs exactly):**

| Company | Ticker | CIK |
|---|---|---|
| Apple Inc. | AAPL | 0000320193 |
| Microsoft Corporation | MSFT | 0000789019 |
| NVIDIA Corporation | NVDA | 0001045810 |
| JPMorgan Chase & Co. | JPM | 0000019617 |
| Walmart Inc. | WMT | 0000104169 |

**Requirements:**

1. **User-Agent on every request.** Define one headers dictionary with `User-Agent: "MIS3060 Villanova atadepal@villanova.edu"` and pass it to every single `requests.get()` call in the script, not just the first one. Pause about 0.2 seconds between requests to stay under the SEC's rate limit of 10 requests per second.

2. **Find earnings filings.** For each company, request `https://data.sec.gov/submissions/CIK{cik}.json`. Inside `filings.recent`, the fields `form`, `items`, `filingDate`, `accessionNumber`, and `primaryDocument` are parallel lists. Keep only filings where `form` is `"8-K"` and the `items` string contains `"2.02"` (Results of Operations).

3. **Take the four most recent.** Sort the matching filings by `filingDate`, newest first, and keep the top four per company (one per quarter).

4. **Get the press release text.** For each filing:
   - Build the filing folder URL: `https://www.sec.gov/Archives/edgar/data/{CIK without leading zeros}/{accession number with dashes removed}/`. Get the list of files from `index.json` in that folder.
   - Identify the earnings press release exhibit, which is usually Exhibit 99.1. Look for an `.htm` file whose name contains `ex99`, `ex-99`, `exhibit99`, or `dex99`. If there are several, prefer 99.1.
   - Download it and strip the HTML to plain text with BeautifulSoup, collapsing extra whitespace.
   - If no exhibit can be found or the download fails, print a warning such as `WARNING [AAPL] 2025-01-30: press release exhibit not found, skipping` and continue to the next filing. The script must never crash on one bad filing.

5. **Extract four fields from the plain text** with regular expressions:
   - `revenue_reported`: total quarterly revenue (or "net sales" or "total net revenue"), kept with its unit, for example `$124.3 billion` or `$65,585 million`
   - `eps_diluted`: diluted earnings per share, for example `$2.40`
   - `net_income`: net income for the quarter, kept with its unit
   - `period`: the reporting period wording, for example `fourth quarter fiscal 2024` or `first quarter 2025`
   
   Different companies word these differently. JPMorgan reports "net revenue" and Walmart reports "total revenues", so write patterns that allow for these variations and take the first match that belongs to the current quarter.

6. **Print each row as it is processed** in this exact format:
   `[Ticker] | [Period] | Revenue: $X | EPS: $X | Net Income: $X`

7. **Save to CSV.** Write all rows to `hw03/earnings_history.csv` with these columns in this order: `company`, `ticker`, `cik`, `filing_date`, `period`, `revenue_reported`, `eps_diluted`, `net_income`. Print a confirmation with the row count when the file is saved.

8. **Missing values are `"NOT_FOUND"`.** If a regex returns no match, store the string `"NOT_FOUND"` in that cell. Never leave a cell blank or write `None`. A blank means we don't know what happened; `"NOT_FOUND"` means we looked and the pattern did not match.

Write the paths so the script works when run from the repo root with `python hw03/hw03_earnings.py`. Add short comments explaining each step.

---

## Specification B: Executive Events Pipeline (Item 5.02)

Write a Python script saved as `hw03/hw03_executives.py` that builds a table of executive departures and appointments for the same five companies from SEC 8-K filings. Use only `requests`, `beautifulsoup4`, and the Python standard library.

**Companies:** the same five companies and CIKs as Specification A (AAPL 0000320193, MSFT 0000789019, NVDA 0001045810, JPM 0000019617, WMT 0000104169).

**Requirements:**

1. **User-Agent on every request.** Use the same headers, `User-Agent: "MIS3060 Villanova atadepal@villanova.edu"`, on every `requests.get()` call, with about a 0.2 second pause between requests.

2. **Find executive change filings.** For each company, request `https://data.sec.gov/submissions/CIK{cik}.json` and use the parallel lists in `filings.recent`. Keep only filings where `form` is `"8-K"`, the `items` string contains `"5.02"` (Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers), and `filingDate` falls within the past 12 months of the day the script runs.

3. **Download and extract.** For each matching filing, download the main 8-K document (`primaryDocument`) from `https://www.sec.gov/Archives/edgar/data/{CIK without leading zeros}/{accession number with dashes removed}/{primaryDocument}` and strip the HTML to plain text. Focus on the text in the Item 5.02 section. From it, extract:
   - `event_type`: `"departure"` (retire, resign, step down, depart, not stand for re-election), `"appointment"` (appoint, elect, name, promote), or `"both"` if one sentence describes a single person doing both, such as moving from one role to another
   - `person_name`: the person's full name
   - `title`: their title or board role, for example `Chief Financial Officer` or `Director`
   - `effective_date`: the date the change takes effect, as written in the filing
   
   If any of these cannot be extracted, store `"NOT_FOUND"` instead of leaving it blank.

4. **One row per event.** If a filing reports more than one event, for example one executive departing and another being appointed, create a separate row for each event. A filing that reports a departure and an appointment must produce two rows.

5. **Print each event as it is processed** in this exact format:
   `[Ticker] | [Date] | [Event Type] | [Name] | [Title]`

6. **Zero events is valid data.** If a company has no Item 5.02 filings in the past 12 months, print `[Ticker]: No executive events in past 12 months` and move on to the next company. This is a finding, not an error, and must not crash the script.

7. **Save to CSV.** Write all events to `hw03/executive_events.csv` with these columns in this order: `company`, `ticker`, `cik`, `filing_date`, `event_type`, `person_name`, `title`, `effective_date`. If no company has any events, still write the file with just the header row. Print a confirmation with the row count when the file is saved.

If a filing fails to download or parse, print a warning and continue to the next filing. Write the paths so the script works when run from the repo root with `python hw03/hw03_executives.py`. Add short comments explaining each step.
