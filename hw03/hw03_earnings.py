"""
HW3 Part 2: Earnings Pipeline (SEC 8-K, Item 2.02)
MIS3060 Business Intelligence with AI | Amon Tadepalli

Builds a quarterly earnings history for five companies from the earnings
press releases (Exhibit 99.1) attached to their 8-K filings on SEC EDGAR.

Run from the repo root:
    python hw03/hw03_earnings.py

Output:
    hw03/earnings_history.csv
"""

import csv
import json
import re
import time

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Step 0: Configuration
# ---------------------------------------------------------------------------

# SEC requires a descriptive User-Agent with a contact email on every request.
# Replace the placeholder with your Villanova email before running.
HEADERS = {"User-Agent": "MIS3060 Villanova atadepal@villanova.edu"}

# Pause between requests to stay well under SEC's 10 requests/second limit.
REQUEST_PAUSE = 0.2

# Number of most recent earnings filings to keep per company (one per quarter).
FILINGS_PER_COMPANY = 4

OUTPUT_CSV = "hw03/earnings_history.csv"
CSV_COLUMNS = [
    "company", "ticker", "cik", "filing_date", "period",
    "revenue_reported", "eps_diluted", "net_income",
]
NOT_FOUND = "NOT_FOUND"

# CIKs are used exactly as given in the assignment.
COMPANIES = [
    {"company": "Apple Inc.",            "ticker": "AAPL", "cik": "0000320193"},
    {"company": "Microsoft Corporation", "ticker": "MSFT", "cik": "0000789019"},
    {"company": "NVIDIA Corporation",    "ticker": "NVDA", "cik": "0001045810"},
    {"company": "JPMorgan Chase & Co.",  "ticker": "JPM",  "cik": "0000019617"},
    {"company": "Walmart Inc.",          "ticker": "WMT",  "cik": "0000104169"},
]


# ---------------------------------------------------------------------------
# Step 1: One helper for every HTTP request (same headers + pause every time)
# ---------------------------------------------------------------------------

def sec_get(url):
    """GET a URL from SEC with the required headers and a polite pause."""
    time.sleep(REQUEST_PAUSE)
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response


# ---------------------------------------------------------------------------
# Step 2 and 3: Find the four most recent 8-K filings with Item 2.02
# ---------------------------------------------------------------------------

def get_earnings_filings(cik):
    """Return the most recent 8-K / Item 2.02 filings for a company, newest first."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = json.loads(sec_get(url).text)
    recent = data["filings"]["recent"]

    # form, items, filingDate, accessionNumber, primaryDocument are parallel lists.
    matches = []
    for i in range(len(recent["form"])):
        form = recent["form"][i]
        items = recent["items"][i] or ""
        if form == "8-K" and "2.02" in items:
            matches.append({
                "filing_date": recent["filingDate"][i],
                "accession": recent["accessionNumber"][i],
                "primary_document": recent["primaryDocument"][i],
            })

    # ISO dates (YYYY-MM-DD) sort correctly as strings.
    matches.sort(key=lambda f: f["filing_date"], reverse=True)
    return matches[:FILINGS_PER_COMPANY]


# ---------------------------------------------------------------------------
# Step 4: Locate and download the press release exhibit, strip to plain text
# ---------------------------------------------------------------------------

EX99_NAME = re.compile(r"(ex-?99|exhibit-?99|dex99)", re.IGNORECASE)
EX991_NAME = re.compile(r"(ex-?99[._-]?0?1|exhibit-?99[._-]?0?1|dex991|ex99d1)", re.IGNORECASE)


def find_press_release_url(cik, accession, primary_document):
    """Return the URL of the Exhibit 99.1 press release, or None if not found."""
    cik_int = str(int(cik))                 # CIK without leading zeros
    acc_nodash = accession.replace("-", "")  # accession number without dashes
    folder = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/"

    # 4a: list the files in the filing folder via index.json
    index = json.loads(sec_get(folder + "index.json").text)
    names = [item["name"] for item in index["directory"]["item"]]
    htm_files = [n for n in names if n.lower().endswith((".htm", ".html"))]

    # 4b: match exhibit names like ex99, ex-99, exhibit99, dex99; prefer 99.1
    ex99 = [n for n in htm_files if EX99_NAME.search(n)]
    if ex99:
        preferred = [n for n in ex99 if EX991_NAME.search(n)]
        return folder + (preferred[0] if preferred else sorted(ex99)[0])

    # 4c: fallback for filers whose exhibit names do not say "ex99"
    # (NVIDIA, for example, names its release like "q2fy26pr.htm").
    # The human-readable filing index lists each document's exhibit type.
    try:
        index_page = sec_get(folder + f"{accession}-index.htm").text
        soup = BeautifulSoup(index_page, "html.parser")
        fallback = None
        for row in soup.find_all("tr"):
            cells = [c.get_text(strip=True) for c in row.find_all("td")]
            link = row.find("a")
            if len(cells) < 4 or link is None:
                continue
            doc_type = cells[3].upper()
            href = link.get("href", "")
            if not href.lower().endswith((".htm", ".html")):
                continue
            if doc_type == "EX-99.1":
                return "https://www.sec.gov" + href
            if doc_type.startswith("EX-99") and fallback is None:
                fallback = "https://www.sec.gov" + href
        if fallback:
            return fallback
    except requests.RequestException:
        pass

    return None


def html_to_text(html):
    """Strip HTML to plain text and collapse whitespace."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(" ")
    text = text.replace("\xa0", " ").replace("’", "'")
    text = text.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Step 5: Extract period, revenue, diluted EPS, and net income with regex
# ---------------------------------------------------------------------------

ORDINALS = {"1": "first", "2": "second", "3": "third", "4": "fourth"}
QTR_WORD = r"(first|second|third|fourth)"

# Dollar amount with a unit, e.g. "$124.3 billion" or "$ 65,585 million"
MONEY = r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(billion|million)"
# Bare table figure, e.g. "$ 14,736" or "7,026"
TABLE_NUM = r"\$?\s?(\d{1,3}(?:,\d{3})+)"

# Words right before a match that mean it is a segment, guidance, or
# non-GAAP figure rather than the company-wide GAAP number we want.
EXCLUDE_CONTEXT = re.compile(
    r"(adjusted|non-gaap|excluding|cloud|data center|gaming|segment|"
    r"outlook|expected|guidance|prior year|year-ago|last year|"
    r"noncontrolling|productivity|intelligent|personal computing|"
    r"professional visualization|automotive|services|sam's club|international)\W*\w*\W*\w*\W*$",
    re.IGNORECASE,
)


def fmt_year(year):
    """Turn '25' into '2025'; leave '2025' alone."""
    return year if len(year) == 4 else "20" + year


def extract_period(text):
    """Return reporting period wording, e.g. 'fourth quarter fiscal 2024'."""
    head = text[:6000]  # the period is stated near the top of the release
    candidates = []  # (position, normalized period)

    patterns = [
        # "fourth quarter of fiscal 2025", "second quarter fiscal year 2026"
        (r"\b" + QTR_WORD + r"[- ]quarter (?:of )?fiscal (?:year )?(\d{4})",
         lambda m: f"{m.group(1).lower()} quarter fiscal {m.group(2)}"),
        # Apple: "fiscal 2025 fourth quarter"
        (r"\bfiscal (?:year )?(\d{4}) " + QTR_WORD + r"[- ]quarter",
         lambda m: f"{m.group(2).lower()} quarter fiscal {m.group(1)}"),
        # Walmart / Microsoft: "Q2 FY26", "Q4 fiscal 2025"
        (r"\bQ([1-4]) (?:FY ?|fiscal (?:year )?)(\d{2,4})\b",
         lambda m: f"{ORDINALS[m.group(1)]} quarter fiscal {fmt_year(m.group(2))}"),
        # Microsoft: "FY25 Q4"
        (r"\bFY ?(\d{2,4}) Q([1-4])\b",
         lambda m: f"{ORDINALS[m.group(2)]} quarter fiscal {fmt_year(m.group(1))}"),
        # JPMorgan (calendar year): "second-quarter 2025", "second quarter 2025"
        (r"\b" + QTR_WORD + r"[- ]quarter (?:of )?(\d{4})\b",
         lambda m: f"{m.group(1).lower()} quarter {m.group(2)}"),
        # Last resort: "quarter ended June 30, 2025"
        (r"\bquarter ended ([A-Z][a-z]+ \d{1,2}, \d{4})",
         lambda m: f"quarter ended {m.group(1)}"),
    ]

    for pattern, build in patterns:
        match = re.search(pattern, head, re.IGNORECASE)
        if match:
            candidates.append((match.start(), build(match)))

    if not candidates:
        return NOT_FOUND
    # The earliest mention is almost always the quarter being reported;
    # later mentions tend to be outlook for the next quarter.
    # Prefer a "quarter ended <date>" only if nothing else matched.
    named = [c for c in candidates if not c[1].startswith("quarter ended")]
    return min(named or candidates)[1]


def first_valid_match(pattern, text, build):
    """Return build(match) for the first match whose preceding words are not excluded."""
    for match in re.finditer(pattern, text, re.IGNORECASE):
        before = text[max(0, match.start() - 40):match.start()]
        # "GAAP and non-GAAP earnings per share were $1.08 and $1.05":
        # the first figure is GAAP, so this phrasing is allowed.
        combined = re.search(r"GAAP and non-GAAP\W*$", before, re.IGNORECASE)
        if EXCLUDE_CONTEXT.search(before) and not combined:
            continue
        return build(match)
    return None


def money(match, amount_group=1, unit_group=2):
    return f"${match.group(amount_group)} {match.group(unit_group).lower()}"


def table_unit(text):
    """Most statements say 'in millions'; fall back to that when unstated."""
    if re.search(r"in thousands", text, re.IGNORECASE) and not re.search(
            r"in millions", text, re.IGNORECASE):
        return "thousand"
    return "million"


def extract_revenue(text):
    """Total quarterly revenue with its unit, e.g. '$124.3 billion'."""
    verbs = r"(?:\s(?:was|were|of|totaled|reached|grew|increased|rose|up|at))?"
    prose = [
        # "quarterly revenue of $94.9 billion", "Revenue was $76.4 billion",
        # "net revenue of $45.7 billion", "Total revenue was $177.4 billion",
        # "reported revenue for the second quarter ended July 27, 2025, of $46.7 billion"
        r"\b(?:total |quarterly |reported |consolidated |record )*(?:net )?revenues?"
        + verbs + r"[^$]{0,80}?" + MONEY,
        r"\b(?:total |quarterly )*net sales" + verbs + r"[^$]{0,80}?" + MONEY,
    ]
    for pattern in prose:
        found = first_valid_match(pattern, text, money)
        if found:
            return found

    # Fallback: income statement line, e.g. "Total net sales $ 94,930"
    table = r"\b(?:total net sales|total revenues?|total net revenue|net revenue|revenues?)\s*" + TABLE_NUM
    unit = table_unit(text)
    found = first_valid_match(table, text, lambda m: f"${m.group(1)} {unit}")
    return found or NOT_FOUND


def extract_eps(text):
    """GAAP diluted EPS, e.g. '$2.40'."""
    eps = r"\$\s?(\d+\.\d{2})"
    patterns = [
        # Apple / Microsoft: "diluted earnings per share of $1.64", "was $3.65"
        r"\bdiluted earnings per share[^$]{0,60}?" + eps,
        # NVIDIA: "GAAP earnings per diluted share for the quarter were $1.08"
        r"\bearnings per diluted share[^$]{0,60}?" + eps,
        # Walmart: "GAAP EPS of $0.88", "Diluted EPS of $..."
        r"\b(?:GAAP |diluted )+EPS[^$]{0,40}?" + eps,
        # JPMorgan: "net income of $15.0 billion, or $5.24 per share"
        eps + r" per (?:diluted )?share",
        # Table fallback: "Diluted $ 0.97" under an earnings-per-share heading
        r"\bdiluted\s*" + eps,
    ]
    for pattern in patterns:
        found = first_valid_match(pattern, text, lambda m: f"${m.group(1)}")
        if found:
            return found
    return NOT_FOUND


def extract_net_income(text):
    """Net income for the quarter with its unit, e.g. '$27.2 billion'."""
    prose = (
        r"\bnet income(?: attributable to [A-Z][\w.&, ]{2,40}?)?"
        r"(?:\s(?:was|were|of|totaled|reached|grew|increased|rose))?[^$]{0,60}?" + MONEY
    )
    found = first_valid_match(prose, text, money)
    if found:
        return found

    # Fallback: income statement line. Prefer the line attributable to the
    # company (Walmart reports consolidated net income before minority interest).
    unit = table_unit(text)
    table_patterns = [
        r"\bnet income attributable to (?!noncontrolling)[A-Z][\w.&, ]{2,40}?\s*" + TABLE_NUM,
        r"\bnet income\s*" + TABLE_NUM,
    ]
    for pattern in table_patterns:
        found = first_valid_match(pattern, text, lambda m: f"${m.group(1)} {unit}")
        if found:
            return found
    return NOT_FOUND


# ---------------------------------------------------------------------------
# Main pipeline: loop over companies and filings, print rows, save CSV
# ---------------------------------------------------------------------------

def process_filing(company, filing):
    """Build one CSV row for a filing. Returns None if the filing must be skipped."""
    ticker = company["ticker"]
    date = filing["filing_date"]

    try:
        url = find_press_release_url(company["cik"], filing["accession"],
                                     filing["primary_document"])
    except (requests.RequestException, ValueError, KeyError) as err:
        print(f"WARNING [{ticker}] {date}: could not read filing index ({err}), skipping")
        return None
    if url is None:
        print(f"WARNING [{ticker}] {date}: press release exhibit not found, skipping")
        return None

    try:
        text = html_to_text(sec_get(url).text)
    except requests.RequestException as err:
        print(f"WARNING [{ticker}] {date}: press release download failed ({err}), skipping")
        return None

    return {
        "company": company["company"],
        "ticker": ticker,
        "cik": company["cik"],
        "filing_date": date,
        "period": extract_period(text),
        "revenue_reported": extract_revenue(text),
        "eps_diluted": extract_eps(text),
        "net_income": extract_net_income(text),
    }


def print_row(row):
    """Print in the required format: [Ticker] | [Period] | Revenue: $X | EPS: $X | Net Income: $X"""
    print(f"{row['ticker']} | {row['period']} | Revenue: {row['revenue_reported']} | "
          f"EPS: {row['eps_diluted']} | Net Income: {row['net_income']}")


def main():
    rows = []

    for company in COMPANIES:
        ticker = company["ticker"]
        print(f"\n=== {company['company']} ({ticker}) ===")

        try:
            filings = get_earnings_filings(company["cik"])
        except (requests.RequestException, ValueError, KeyError) as err:
            print(f"WARNING [{ticker}]: could not load EDGAR submissions ({err}), skipping company")
            continue

        if not filings:
            print(f"WARNING [{ticker}]: no 8-K Item 2.02 filings found")
            continue

        for filing in filings:
            try:
                row = process_filing(company, filing)
            except Exception as err:  # never let one bad filing crash the run
                print(f"WARNING [{ticker}] {filing['filing_date']}: unexpected error ({err}), skipping")
                continue
            if row is None:
                continue

            # Guarantee no blank or None cells: missing data is "NOT_FOUND".
            for col in CSV_COLUMNS:
                if row.get(col) in (None, ""):
                    row[col] = NOT_FOUND

            print_row(row)
            rows.append(row)

    # Step 7: save all rows to CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
