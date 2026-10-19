# HW3 AI Usage Log

## Prompts Sent to Claude Cowork

Each prompt was sent in a new Cowork conversation. Specifications A and B were pasted exactly as written in `specifications.md`.

### Prompt 1: Specification A (earnings pipeline, produced `hw03_earnings.py`)

> Write a Python script saved as `hw03/hw03_earnings.py` that builds a quarterly earnings history for five companies from SEC 8-K earnings press releases. Use only `requests`, `beautifulsoup4`, and the Python standard library (`re`, `csv`, `time`, `json`).
>
> **Companies (use these CIKs exactly):**
>
> | Company | Ticker | CIK |
> |---|---|---|
> | Apple Inc. | AAPL | 0000320193 |
> | Microsoft Corporation | MSFT | 0000789019 |
> | NVIDIA Corporation | NVDA | 0001045810 |
> | JPMorgan Chase & Co. | JPM | 0000019617 |
> | Walmart Inc. | WMT | 0000104169 |
>
> **Requirements:**
>
> 1. **User-Agent on every request.** Define one headers dictionary with `User-Agent: "MIS3060 Villanova atadepal@villanova.edu"` and pass it to every single `requests.get()` call in the script, not just the first one. Pause about 0.2 seconds between requests to stay under the SEC's rate limit of 10 requests per second.
>
> 2. **Find earnings filings.** For each company, request `https://data.sec.gov/submissions/CIK{cik}.json`. Inside `filings.recent`, the fields `form`, `items`, `filingDate`, `accessionNumber`, and `primaryDocument` are parallel lists. Keep only filings where `form` is `"8-K"` and the `items` string contains `"2.02"` (Results of Operations).
>
> 3. **Take the four most recent.** Sort the matching filings by `filingDate`, newest first, and keep the top four per company (one per quarter).
>
> 4. **Get the press release text.** For each filing:
>    - Build the filing folder URL: `https://www.sec.gov/Archives/edgar/data/{CIK without leading zeros}/{accession number with dashes removed}/`. Get the list of files from `index.json` in that folder.
>    - Identify the earnings press release exhibit, which is usually Exhibit 99.1. Look for an `.htm` file whose name contains `ex99`, `ex-99`, `exhibit99`, or `dex99`. If there are several, prefer 99.1.
>    - Download it and strip the HTML to plain text with BeautifulSoup, collapsing extra whitespace.
>    - If no exhibit can be found or the download fails, print a warning such as `WARNING [AAPL] 2025-01-30: press release exhibit not found, skipping` and continue to the next filing. The script must never crash on one bad filing.
>
> 5. **Extract four fields from the plain text** with regular expressions:
>    - `revenue_reported`: total quarterly revenue (or "net sales" or "total net revenue"), kept with its unit, for example `$124.3 billion` or `$65,585 million`
>    - `eps_diluted`: diluted earnings per share, for example `$2.40`
>    - `net_income`: net income for the quarter, kept with its unit
>    - `period`: the reporting period wording, for example `fourth quarter fiscal 2024` or `first quarter 2025`
>    
>    Different companies word these differently. JPMorgan reports "net revenue" and Walmart reports "total revenues", so write patterns that allow for these variations and take the first match that belongs to the current quarter.
>
> 6. **Print each row as it is processed** in this exact format:
>    `[Ticker] | [Period] | Revenue: $X | EPS: $X | Net Income: $X`
>
> 7. **Save to CSV.** Write all rows to `hw03/earnings_history.csv` with these columns in this order: `company`, `ticker`, `cik`, `filing_date`, `period`, `revenue_reported`, `eps_diluted`, `net_income`. Print a confirmation with the row count when the file is saved.
>
> 8. **Missing values are `"NOT_FOUND"`.** If a regex returns no match, store the string `"NOT_FOUND"` in that cell. Never leave a cell blank or write `None`. A blank means we don't know what happened; `"NOT_FOUND"` means we looked and the pattern did not match.
>
> Write the paths so the script works when run from the repo root with `python hw03/hw03_earnings.py`. Add short comments explaining each step.

### Prompt 2: Specification B (executive events pipeline, produced `hw03_executives.py`)

> Write a Python script saved as `hw03/hw03_executives.py` that builds a table of executive departures and appointments for the same five companies from SEC 8-K filings. Use only `requests`, `beautifulsoup4`, and the Python standard library.
>
> **Companies:** the same five companies and CIKs as Specification A (AAPL 0000320193, MSFT 0000789019, NVDA 0001045810, JPM 0000019617, WMT 0000104169).
>
> **Requirements:**
>
> 1. **User-Agent on every request.** Use the same headers, `User-Agent: "MIS3060 Villanova atadepal@villanova.edu"`, on every `requests.get()` call, with about a 0.2 second pause between requests.
>
> 2. **Find executive change filings.** For each company, request `https://data.sec.gov/submissions/CIK{cik}.json` and use the parallel lists in `filings.recent`. Keep only filings where `form` is `"8-K"`, the `items` string contains `"5.02"` (Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers), and `filingDate` falls within the past 12 months of the day the script runs.
>
> 3. **Download and extract.** For each matching filing, download the main 8-K document (`primaryDocument`) from `https://www.sec.gov/Archives/edgar/data/{CIK without leading zeros}/{accession number with dashes removed}/{primaryDocument}` and strip the HTML to plain text. Focus on the text in the Item 5.02 section. From it, extract:
>    - `event_type`: `"departure"` (retire, resign, step down, depart, not stand for re-election), `"appointment"` (appoint, elect, name, promote), or `"both"` if one sentence describes a single person doing both, such as moving from one role to another
>    - `person_name`: the person's full name
>    - `title`: their title or board role, for example `Chief Financial Officer` or `Director`
>    - `effective_date`: the date the change takes effect, as written in the filing
>    
>    If any of these cannot be extracted, store `"NOT_FOUND"` instead of leaving it blank.
>
> 4. **One row per event.** If a filing reports more than one event, for example one executive departing and another being appointed, create a separate row for each event. A filing that reports a departure and an appointment must produce two rows.
>
> 5. **Print each event as it is processed** in this exact format:
>    `[Ticker] | [Date] | [Event Type] | [Name] | [Title]`
>
> 6. **Zero events is valid data.** If a company has no Item 5.02 filings in the past 12 months, print `[Ticker]: No executive events in past 12 months` and move on to the next company. This is a finding, not an error, and must not crash the script.
>
> 7. **Save to CSV.** Write all events to `hw03/executive_events.csv` with these columns in this order: `company`, `ticker`, `cik`, `filing_date`, `event_type`, `person_name`, `title`, `effective_date`. If no company has any events, still write the file with just the header row. Print a confirmation with the row count when the file is saved.
>
> If a filing fails to download or parse, print a warning and continue to the next filing. Write the paths so the script works when run from the repo root with `python hw03/hw03_executives.py`. Add short comments explaining each step.

### Prompt 3: Timeline (produced `hw03_timeline.py`)

> Write a Python script that reads `hw03/earnings_history.csv` and `hw03/executive_events.csv`. Do the following:
>
> 1. For each executive event in the events table, calculate the number of days between the executive event's `filing_date` and the nearest earnings filing date for the same company in the earnings table. Call this `days_to_nearest_earnings`.
> 2. Add a column `event_timing` that categorizes each executive event as: `'before earnings'` if the event came before the nearest earnings filing, `'after earnings'` if it came after, or `'same week'` if within 7 days of an earnings filing.
> 3. Save the combined table to `hw03/corporate_events_timeline.csv` with all columns from both source tables plus `days_to_nearest_earnings` and `event_timing`.
> 4. Print a summary: for each company, list any executive events and whether they occurred before or after the nearest earnings announcement.
> 5. Print a final count: how many events occurred before vs. after an earnings announcement across all five companies.

### Prompt 4: yfinance cross-check for Part 5C (produced `hw03_yfinance_check.py`)

Cowork generated this script while helping me draft `validation.md`, based on the assignment's suggested prompt: *"Write Python using yfinance to get the most recent quarterly revenue and net income for [ticker]."* I used AAPL as the ticker and ran it myself to fill in the 5C table.

## Extractions That Required Iteration

None of the five companies needed a follow-up regex fix. The earnings pipeline returned all 20 rows (5 companies x 4 quarters) with zero `NOT_FOUND` values on the first successful run, and the Apple values matched both the official press release and yfinance in Part 5.

The only rerun was not a regex issue: the first run failed for all five companies with a DNS error (`getaddrinfo failed`) because my network was off. The script printed a warning for each company and saved an empty CSV instead of crashing, which confirmed the error handling worked. After reconnecting, it ran cleanly.

Two executive events have `NOT_FOUND` for `effective_date` (Chris Kondo at Apple, Marianne Lake at JPMorgan). I left these as-is since storing `NOT_FOUND` is the behavior the spec asks for.

## Something the Script Did That I Did Not Specify

The executive events script added a filter (`is_past_bio`) that skips sentences describing someone's past career, like "joined Apple in 2013" or "was appointed in 2019". I never thought to specify this, but without it, the biography paragraphs that 8-Ks include for new appointees would have created fake "appointment" rows for jobs people took years ago. Looking at the output, it was correct: every event in `executive_events.csv` is a current change, not a past role.

A second example from the timeline script: both source tables have a `filing_date` column, so it renamed the earnings one to `earnings_filing_date` instead of overwriting it. The prompt said to keep "all columns from both source tables" but didn't say how to handle the name conflict. This was also correct and kept both dates in the final CSV.
