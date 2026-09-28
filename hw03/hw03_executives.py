"""
HW3 Part 3: Executive Events Pipeline (SEC 8-K, Item 5.02)
MIS3060 Business Intelligence with AI | Amon Tadepalli

Builds a table of executive departures and appointments for five companies
from the Item 5.02 section of their 8-K filings on SEC EDGAR (past 12 months).

Run from the repo root:
    python hw03/hw03_executives.py

Output:
    hw03/executive_events.csv
"""

import csv
import datetime
import json
import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Step 0: Configuration
# ---------------------------------------------------------------------------

# SEC requires a descriptive User-Agent with a contact email on every request.
HEADERS = {"User-Agent": "MIS3060 Villanova atadepal@villanova.edu"}

# Pause between requests to stay well under SEC's 10 requests/second limit.
REQUEST_PAUSE = 0.2

# Save next to this script so the path works from the repo root (or anywhere).
OUTPUT_CSV = Path(__file__).resolve().parent / "executive_events.csv"
CSV_COLUMNS = [
    "company", "ticker", "cik", "filing_date",
    "event_type", "person_name", "title", "effective_date",
]
NOT_FOUND = "NOT_FOUND"

# Same five companies and CIKs as Specification A.
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
# Step 2: Find 8-K filings with Item 5.02 from the past 12 months
# ---------------------------------------------------------------------------

def one_year_ago(today):
    """Same calendar day last year (Feb 29 falls back to Feb 28)."""
    try:
        return today.replace(year=today.year - 1)
    except ValueError:
        return today.replace(year=today.year - 1, day=28)


def get_executive_filings(cik, cutoff):
    """Return 8-K / Item 5.02 filings filed on or after cutoff, oldest first."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = json.loads(sec_get(url).text)
    recent = data["filings"]["recent"]

    # form, items, filingDate, accessionNumber, primaryDocument are parallel lists.
    matches = []
    for i in range(len(recent["form"])):
        form = recent["form"][i]
        items = recent["items"][i] or ""
        filing_date = recent["filingDate"][i]
        # ISO dates (YYYY-MM-DD) compare correctly as strings.
        if form == "8-K" and "5.02" in items and filing_date >= cutoff.isoformat():
            matches.append({
                "filing_date": filing_date,
                "accession": recent["accessionNumber"][i],
                "primary_document": recent["primaryDocument"][i],
            })

    matches.sort(key=lambda f: f["filing_date"])
    return matches


# ---------------------------------------------------------------------------
# Step 3: Download the main 8-K document and isolate the Item 5.02 section
# ---------------------------------------------------------------------------

def filing_url(cik, accession, primary_document):
    cik_int = str(int(cik))                  # CIK without leading zeros
    acc_nodash = accession.replace("-", "")  # accession number without dashes
    return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{primary_document}"


def html_to_text(html):
    """Strip HTML to plain text, normalize quotes/dashes, collapse whitespace."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    # Inline XBRL filings hide a metadata block; drop it so it doesn't leak in.
    for tag in soup.find_all(["ix:header"]):
        tag.decompose()
    text = soup.get_text(" ")
    for old, new in {"\xa0": " ", "’": "'", "‘": "'", "“": '"',
                     "”": '"', "–": "-", "—": "-"}.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()


ITEM_502 = re.compile(r"\bItem\s*5\.02\b", re.IGNORECASE)
NEXT_ITEM = re.compile(r"\bItem\s*(?!5\.02)\d\.\d\d\b|\bSIGNATURES?\b", re.IGNORECASE)

# The long Item 5.02 heading contains "Departure", "Election", "Appointment",
# so it must be removed before looking for event verbs.
ITEM_502_HEADING = re.compile(
    r"^Item\s*5\.02\.?\s*(?:\([a-e]\)\s*)?"
    r"(?:(?:Departure|Election|Appointment|Compensatory Arrangements)[^.;]*?[.;]\s*)*",
    re.IGNORECASE,
)


def item_502_section(text):
    """Return the text of the Item 5.02 section (longest block if listed twice)."""
    best = ""
    for match in ITEM_502.finditer(text):
        rest = text[match.start():]
        end = NEXT_ITEM.search(rest, 10)
        block = rest[:end.start()] if end else rest
        if len(block) > len(best):
            best = block
    if not best:
        return text  # heading not found: fall back to the whole document
    best = ITEM_502_HEADING.sub("", best)
    best = re.sub(r"\(\s*[a-e]\s*\)\s*", "", best)  # drop "(b)", "(c)" labels
    # NVIDIA-style shorthand: "Vice President, or VP, and Chief Accounting Officer"
    return re.sub(r",\s+or\s+(?:the\s+)?[A-Z][\w&-]*(?:\s[A-Z][\w&-]*){0,2},", "", best)


# ---------------------------------------------------------------------------
# Step 4: Regex building blocks for names, titles, dates, and event verbs
# ---------------------------------------------------------------------------

HONORIFIC = r"(?:Mr|Ms|Mrs|Dr)\.\s"
NAME_TOKEN = r"[A-Z][a-zA-Z'\-]+"
# "Kevan Parekh", "John R. Furner", "C. Douglas McMillon", "Mr. Parekh"
NAME = re.compile(
    rf"(?:{HONORIFIC})?(?:[A-Z]\.\s)?{NAME_TOKEN}(?:\s[A-Z]\.)?(?:\s{NAME_TOKEN}){{0,2}}(?:,?\sJr\.)?"
)

# Capitalized words that are never part of a person's name.
NOT_NAME_WORDS = {
    "The", "A", "An", "On", "In", "As", "At", "By", "For", "Of", "To", "Upon", "Following",
    "Effective", "Prior", "During", "After", "Before", "His", "Her", "Their", "Such", "This",
    "That", "Each", "Any", "No", "There", "It", "He", "She", "They", "We", "Our", "Also",
    "Company", "Company's", "Board", "Board's", "Directors", "Director", "Chief", "Officer",
    "Executive", "Financial", "Operating", "Accounting", "Legal", "People", "Technology",
    "President", "Vice", "Senior", "General", "Counsel", "Secretary", "Treasurer", "Chair",
    "Chairman", "Lead", "Independent", "Committee", "Compensation", "Nominating", "Audit",
    "Governance", "Corporate", "Management", "Development", "Annual", "Meeting", "Plan",
    "Agreement", "Letter", "Stock", "Shareholders", "Stockholders", "Securities", "Exchange",
    "Act", "Form", "Item", "Section", "Regulation", "Exhibit", "Press", "Release", "Inc",
    "Inc.", "Corporation", "Co", "Co.", "LLC", "Apple", "Apple's", "Microsoft", "Microsoft's",
    "NVIDIA", "NVIDIA's", "JPMorgan", "Chase", "Walmart", "Walmart's", "Sam's", "Club",
    "U.S.", "International", "Global", "Operations", "Services", "Affairs", "Policy",
    "Environment", "Social", "Initiatives", "Human", "Resources", "Strategy", "Machine",
    "Learning", "Retail", "Consumer", "Community", "Banking", "Commercial", "Investment",
    "Bank", "Asset", "Wealth", "Delaware", "California", "Washington", "Arkansas", "New",
    "York", "Retirement", "Transition", "Appointment", "Departure", "Election", "Current",
    "Report", "Registrant", "Fiscal", "Year", "Quarter", "CEO", "CFO", "COO", "Non-Employee",
    "January", "February", "March", "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "Hardware", "Engineering", "Software", "Awards",
    "Retention", "Continuity", "Worldwide", "Field", "Sales", "Solutions", "Messrs", "Firm",
    "Chair's", "Committee's", "Proxy", "Statement", "Director's", "Co-President", "Co-Presidents",
}

TITLE_UNIT = (
    r"(?:(?:executive|senior|group|corporate)\s)*vice president"
    r"(?:(?:, | of )(?-i:[A-Z][\w&']*(?: (?:and |& )?[A-Z][\w&']*){0,3})(?= of |[,.;(]| and [a-z]))?"
    r"|(?:co-)?chief [a-z]+(?: [a-z]+){0,2} officers?"
    r"|principal (?:executive|financial|accounting) officer"
    r"|(?:co-)?presidents?"
    r"|(?:co-|sole )?(?:ceo|cfo|coo|cao|cto|clo|svp|evp|vp)s?\b(?: of (?-i:[A-Z][\w&]*(?: [A-Z&][\w&]*){0,3}))?"
    r"|general counsel"
    r"|(?:corporate )?secretary"
    r"|treasurer|controller"
    r"|(?:executive |non-executive )?chair(?:man|woman|person)?(?: of the board(?: of directors)?)?"
    r"|lead independent director"
    r"|(?:a )?member of (?:the|its|our) (?:company's )?board(?: of directors)?"
    r"|(?:independent |non-employee )?director\b"
)
# Chain units joined by "and" or commas: "Senior Vice President and Chief Financial Officer"
TITLE = re.compile(rf"\b(?:{TITLE_UNIT})(?:(?:,\s|\sand\s|,\sand\s)(?:{TITLE_UNIT}))*", re.IGNORECASE)

MONTHS = (r"(?:January|February|March|April|May|June|July|August|September|"
          r"October|November|December)")
DATE = (rf"(?:{MONTHS}\s\d{{1,2}},\s\d{{4}}|{MONTHS}\s\d{{4}}|"
        r"(?:early|mid-?|late|the end of)\s?\d{4}|\d{1,2}/\d{1,2}/\d{2,4})")
DATE_RE = re.compile(DATE)
# "effective March 1, 2026", "effective immediately", "effective as of the conclusion of ..."
# Lowercase "effective" only, so the defined term "Effective Date" is not a match.
EFFECTIVE_RE = re.compile(rf"(?:\beffective|^Effective)\s(?:as of\s|on\s)?({DATE}|immediately|[a-z][^.;]{{2,120}})")
# Defined dates: 'September 1, 2026 (the "Transition Date")'
DEFINED_DATE_RE = re.compile(rf'({DATE})\s*\((?:the\s)?"([^"]{{3,40}})"\)')
MEETING_RE = re.compile(
    r"\b(?:at|following|as of|upon|until|immediately prior to) the (?:conclusion of the )?"
    r"(?:\w+'s )?(?:(?:June |May )?\d{4} )?annual (?:shareholders'? |stockholders'? |shareholder |stockholder )?"
    r"meeting(?: of (?:shareholders|stockholders))?", re.IGNORECASE)

DEPARTURE_VERB = re.compile(
    r"\b(?:retir(?:e|es|ed|ing|ement)|resign(?:s|ed|ing|ation)?|step(?:s|ped|ping)? down|"
    r"depart(?:s|ed|ing|ure)?|leav(?:e|es|ing)|left|"
    # verb forms only: "will transition", "transitioning" (not "transition plan")
    r"(?:will|to|would|shall) transition|transition(?:s|ed|ing)|"
    r"not (?:to )?stand for re-?election|not be standing for re-?election|"
    r"(?:will|would) not be (?:re-?)?nominated)\b",
    re.IGNORECASE,
)
APPOINTMENT_VERB = re.compile(
    r"\b(?:appoint(?:s|ed|ing|ment)?|elect(?:s|ed|ing|ion)?|name[sd]?|naming|"
    r"promot(?:e|es|ed|ing|ion)|join(?:s|ed|ing)?|hire[sd]?|become[s]?|"
    r"succeed(?:s|ed)?|to serve as|will serve as)\b",
    re.IGNORECASE,
)
# Phrases that contain event words but are not events.
FALSE_EVENT = re.compile(
    r"named executive officers?|re-?elect|election of directors|become effective|"
    r"(?:name|appoint|elect|find|identify)\w*\s(?:a|his|her|their)\s(?:successor|replacement)|"
    r"prior to (?:joining|becoming)|left blank|continues? to serve as|"
    r"(?:elected|elect) not to use",
    re.IGNORECASE,
)
# Boilerplate sentences that mention the person but never describe an event.
SKIP_SENTENCE = re.compile(
    r"family relationship|arrangements? or understandings?|Item 404|Regulation S-K|"
    r"forward-looking|incorporated (?:herein )?by reference|filed (?:as|herewith)",
    re.IGNORECASE,
)


def split_sentences(section):
    """Split on periods, protecting abbreviations like 'Mr.' and initials like 'R.'."""
    protected = re.sub(r"\b(Mr|Ms|Mrs|Dr|Jr|Inc|Co|Corp|No|St|Messrs)\.", r"\1<DOT>", section)
    protected = re.sub(r"\b([A-Z])\.(?=\s?[A-Z])", r"\1<DOT>", protected)
    protected = protected.replace("U.S.", "U<DOT>S<DOT>")
    # Split after ".", including before a footnote marker: "... immediately. 1 In addition"
    parts = re.split(r"(?<=[.!?])\s+(?:\d{1,2}\s+)?(?=[A-Z\"(])", protected)
    return [p.replace("<DOT>", ".").strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Step 5: Find people, events, titles, and dates inside each sentence
# ---------------------------------------------------------------------------

def clean_name(raw):
    """Drop possessive 's and trailing punctuation."""
    return re.sub(r"'s?$", "", raw.strip().rstrip(","))


def find_names(sentence):
    """Return (start, end, name) for every person name in a sentence."""
    found = []
    for match in NAME.finditer(sentence):
        name = clean_name(match.group(0))
        has_honorific = re.match(HONORIFIC, name) is not None
        tokens = re.sub(HONORIFIC, "", name).replace(",", "").split()
        if not tokens:
            continue
        words = [t for t in tokens if not re.fullmatch(r"[A-Z]\.|Jr\.", t)]
        if any(t in NOT_NAME_WORDS or t.rstrip("'s") in NOT_NAME_WORDS for t in words):
            continue
        # A bare single word only counts if it follows "Mr."/"Ms." etc.
        if len(words) < 2 and not has_honorific:
            continue
        found.append((match.start(), match.start() + len(match.group(0)), name))
    return found


def resolve_name(name, known):
    """Map 'Mr. Parekh' or 'Ms. Nora Johnson' back to a full name seen earlier."""
    rest = re.sub(HONORIFIC, "", name)
    if rest != name:
        # Longest known full name that ends with what follows "Mr."/"Ms."
        matches = [full for full in known.values() if full.endswith(rest)]
        if matches:
            return max(matches, key=len)
        if len([t for t in rest.split() if not re.fullmatch(r"[A-Z]\.", t)]) < 2:
            return name  # bare "Mr. Parekh" with no full name yet
        name = rest  # "Mr. John R. Furner" -> "John R. Furner"
    known[name.replace(", Jr.", "").split()[-1]] = name
    return name


def pick_person(sentence, verb, names):
    """Choose which name a verb belongs to.

    1. A name right after the verb, joined only by lowercase words
       ("appointed Kevan Parekh", "the retirement of Jane Doe").
    2. Otherwise the closest name before the verb (the subject).
    3. Otherwise the closest name after it.
    """
    if not names:
        return None
    word = verb.group(0).lower()
    after = [n for n in names if n[0] >= verb.end()]
    before = [n for n in names if n[1] <= verb.start()]

    # "X will succeed Mr. Y": X is appointed, so skip rule 1 for plain "succeed".
    plain_succeed = word.startswith("succeed") and not re.match(r"\s+by\b", sentence[verb.end():])
    if after and not plain_succeed:
        gap = sentence[verb.end():after[0][0]]
        if len(gap) <= 45 and re.fullmatch(r"[\sa-z']*", gap):
            return after[0]
    if before:
        return before[-1]
    return after[0] if after else None


def nearest_title(sentence, anchor, prefer_after):
    """Return the title closest to a position in the sentence."""
    titles = list(TITLE.finditer(sentence))
    if not titles:
        return None
    if prefer_after:
        later = [t for t in titles if t.start() >= anchor]
        if later:
            titles = later

    def distance(t):
        return abs(t.start() - anchor) if t.start() >= anchor else abs(anchor - t.end())
    return normalize_title(min(titles, key=distance).group(0))


def new_title(sentence, verb, only_to=False):
    """Title someone is taking on: prefer 'as <title>' / 'to <title>' after the verb."""
    after = sentence[verb.end():]
    words = "to" if only_to else "as|to|become|becomes"
    lead_re = re.compile(rf"\b(?:{words}) (?:the role of |the position of |serve as |become )?"
                         r"(?:a |an |the |its |\w+'s )?(?=[A-Za-z])")
    # "will become sole CEO of the CIB": title right after the verb
    direct = TITLE.match(after, len(after) - len(after.lstrip()))
    if direct and not only_to:
        return normalize_title(direct.group(0))
    for lead in lead_re.finditer(after):
        title = TITLE.match(after, lead.end())
        if title:
            return normalize_title(title.group(0))
    return nearest_title(sentence, verb.end(), prefer_after=True)


def normalize_title(title):
    """Title-case the role and turn board-seat wording into 'Director'."""
    title = title.strip(" ,")
    title = re.sub(r"(?:a )?member of (?:the|its|our) (?:company's )?board(?: of directors)?|"
                   r"(?<!lead )\b(?:independent |non-employee )?director\b", "Director", title, flags=re.IGNORECASE)
    # "Co-Presidents" -> "Co-President"
    title = re.sub(r"\b(President|CEO|Officer|Director)s\b", r"\1", title, flags=re.IGNORECASE)
    # "VP and CAO of the Company" -> "VP and CAO"
    title = re.sub(r"\s+of (?:the )?(?:Company|Firm)$", "", title, flags=re.IGNORECASE)
    small = {"and", "of", "the"}
    words = []
    for w in title.split():
        if w.isupper() or re.fullmatch(r"(?:Co-|co-)?[A-Z]{2,5}s?", w):  # keep CEO, CFO, VP
            words.append(w)
        elif w.lower() in small:
            words.append(w.lower())
        else:
            words.append("-".join(part[:1].upper() + part[1:].lower() for part in w.split("-")))
    return " ".join(words)


def board_title(sentence, event_type):
    """Director elections often say 'elected to the Board' with no title word."""
    if event_type != "departure" and re.search(r"\bto (?:the|its|our) (?:\w+'s )?Board\b", sentence):
        return "Director"
    if event_type != "appointment" and re.search(
            r"\b(?:from (?:the|its|our) (?:\w+'s )?Board|re-?election)\b", sentence, re.IGNORECASE):
        return "Director"
    return None


def trim_effective(phrase):
    """'upon ... with the Company on May 4, 2026, and ...' -> stop right after the date."""
    date = DATE_RE.search(phrase)
    if date:
        return phrase[:date.end()].strip()
    return phrase.split(",")[0].strip()


def apply_defined_dates(phrase, defined):
    """Swap a defined term like 'the Transition Date' for the actual date."""
    for term, date in defined.items():
        if term in phrase:
            return date
    return phrase


def find_effective_date(sentence, anchor, defined):
    """Return the effective date as written: 'effective ...' first, else the closest date."""
    match = EFFECTIVE_RE.search(sentence)
    if match:
        return apply_defined_dates(trim_effective(match.group(1)), defined)
    # Board changes are often tied to the annual meeting instead of a calendar date.
    meeting = MEETING_RE.search(sentence)
    if meeting:
        return meeting.group(0)
    # "... will become Lead Independent Director on the Transition Date"
    for term, date in defined.items():
        if re.search(rf"\b(?:on|as of|from) the {re.escape(term)}", sentence):
            return date
    dates = []
    for d in DATE_RE.finditer(sentence):
        # Skip the announcement date at the start: "On December 4, 2025, Apple announced ..."
        if re.match(r"\s*(?:On|As of)\s*$", sentence[:d.start()], re.IGNORECASE):
            continue
        # Skip past-tense biography dates: "since November 2019", "in 2013"
        if re.search(r"(?:since|from|between)\s*$", sentence[:d.start()], re.IGNORECASE):
            continue
        dates.append(d)
    if not dates:
        return None
    return min(dates, key=lambda d: abs(d.start() - anchor)).group(0)


def is_past_bio(sentence, verb):
    """'joined Apple in 2013' or 'was appointed in 2019' is history, not news."""
    tail = sentence[verb.end():verb.end() + 45]
    return re.search(rf"\b(?:in|since) (?:{MONTHS} )?(?:19|20)\d\d\b", tail) is not None and \
        not re.search(r"\bwill\b", sentence[:verb.start()][-30:])


def extract_events(section):
    """Return a list of event dicts (one per person per event type) from Item 5.02 text."""
    known_names = {}
    events = {}   # (person, event_type) -> event dict, keeps insertion order
    defined = {term: date for date, term in DEFINED_DATE_RE.findall(section)}

    for sentence in split_sentences(section):
        if SKIP_SENTENCE.search(sentence):
            continue
        names = find_names(sentence)
        names = [(s, e, resolve_name(n, known_names)) for s, e, n in names]

        # Blank out false positives (e.g. "named executive officers") so those
        # words are not read as appointments. Departures scan the raw sentence
        # so "not stand for re-election" survives.
        scan = {"departure": sentence,
                "appointment": FALSE_EVENT.sub(lambda m: " " * len(m.group(0)), sentence)}

        # person -> {"departure": verb match, "appointment": verb match}
        per_person = {}
        for kind, pattern in (("departure", DEPARTURE_VERB), ("appointment", APPOINTMENT_VERB)):
            for verb in pattern.finditer(scan[kind]):
                if is_past_bio(sentence, verb):
                    continue
                person = pick_person(sentence, verb, names)
                if person is None:
                    continue
                # "X will succeed Mr. Y": the person after "succeed" is the one leaving.
                if kind == "appointment" and verb.group(0).lower().startswith("succeed") \
                        and not re.match(r"\s+by\b", sentence[verb.end():]):
                    successor = pick_person(sentence, verb, [n for n in names if n[1] <= verb.start()])
                    predecessor = [n for n in names if n[0] >= verb.end()]
                    if predecessor:
                        per_person.setdefault(predecessor[0][2], {}).setdefault("departure", (verb, predecessor[0]))
                    if successor is None:
                        continue
                    person = successor
                per_person.setdefault(person[2], {}).setdefault(kind, (verb, person))
                # "Doug Petno, 61, and Troy Rohrbaugh, 56, ... have been elected": both people.
                idx = names.index(person)
                while idx > 0 and person[1] <= verb.start() and re.fullmatch(
                        r"(?:,\s*(?:age\s)?\d{2})?,?\s+and\s+", sentence[names[idx - 1][1]:names[idx][0]]):
                    idx -= 1
                    per_person.setdefault(names[idx][2], {}).setdefault(kind, (verb, names[idx]))
                # "will transition from CEO to Executive Chair": leaving one role for another.
                if kind == "departure" and "transition" in verb.group(0).lower():
                    new_role = re.match(r"(?:(?!\bto\b)[^.;])*?\bto (?:the role of |the position of |serve as |"
                                        r"become )?(?:a |an |the |\w+'s )?(?=[A-Za-z])",
                                        sentence[verb.end():])
                    if new_role and TITLE.match(sentence, verb.end() + new_role.end()):
                        per_person[person[2]].setdefault("appointment", (verb, person))

        for person, kinds in per_person.items():
            # Same person leaving one role and taking another in one sentence = "both".
            event_type = "both" if len(kinds) == 2 else next(iter(kinds))
            verb, name_span = kinds.get("appointment") or kinds["departure"]
            # "Art Levinson, current Chair of the Board, will become Lead Independent Director"
            if event_type == "appointment" and name_span[1] <= verb.start() and re.search(
                    r"\bcurrent(?:ly)?\b", sentence[name_span[1]:verb.start()]) and \
                    TITLE.search(sentence[name_span[1]:verb.start()]):
                event_type = "both"

            if event_type == "both":
                # Moving roles: report "old role -> new role" when both appear.
                old = nearest_title(sentence[:verb.start()], name_span[1], prefer_after=False)
                # "will transition from his role as Chief Executive Officer to ..."
                from_role = re.match(r"\s+from (?:his |her |their |the )?(?:current )?(?:role |position )?(?:as |of )?"
                                     r"(?:the )?(?:\w+'s )?", sentence[verb.end():])
                if from_role:
                    match = TITLE.match(sentence, verb.end() + from_role.end())
                    old = normalize_title(match.group(0)) if match else old
                new = new_title(sentence, verb, only_to="transition" in verb.group(0).lower())
                title = f"{old} -> {new}" if old and new and old != new else (new or old)
            elif event_type == "appointment":
                title = new_title(sentence, verb)
            else:
                title = nearest_title(sentence, name_span[1], prefer_after=False)
            title = title or board_title(sentence, event_type)

            date = find_effective_date(sentence, verb.start(), defined)

            # Merge with an earlier row for the same person and event.
            key = (person, event_type)
            if key in events:
                row = events[key]
                if title and row["title"] == NOT_FOUND:
                    row["title"] = title
                elif title and title not in row["title"]:
                    # e.g. new CEO also elected to the Board: "... Officer; Director"
                    row["title"] += f"; {title}"
                if date and row["effective_date"] == NOT_FOUND:
                    row["effective_date"] = date
                continue
            # A later "both" for someone already logged replaces their single rows.
            if event_type == "both":
                for k in ("departure", "appointment"):
                    events.pop((person, k), None)
            elif (person, "both") in events:
                continue

            events[key] = {
                "event_type": event_type,
                "person_name": person,
                "title": title or NOT_FOUND,
                "effective_date": date or NOT_FOUND,
            }

    # If the section states exactly one effective date, use it for rows
    # whose own sentence did not say when the change takes effect.
    section_dates = {apply_defined_dates(trim_effective(m.group(1)), defined)
                     for s in split_sentences(section) for m in EFFECTIVE_RE.finditer(s)}
    for row in events.values():
        if row["event_type"] == "appointment" and row["effective_date"] == NOT_FOUND \
                and len(section_dates) == 1:
            row["effective_date"] = next(iter(section_dates))

    # Fill gaps from other sentences that mention the same person.
    sentences = split_sentences(section)
    for row in events.values():
        surname = row["person_name"].split()[-1]
        about = [s for s in sentences if re.search(rf"\b{re.escape(surname)}\b", s)]
        if row["title"] == NOT_FOUND:
            # "Kate Adams, who has served as Apple's general counsel since 2017"
            for s in about:
                pos = s.find(row["person_name"])
                title = TITLE.search(s[pos:pos + 120]) if pos >= 0 else None
                if title:
                    row["title"] = normalize_title(title.group(0))
                    break
        if row["effective_date"] == NOT_FOUND:
            # "Ms. McLay will remain in her current position effective as of ..."
            for s in about:
                match = EFFECTIVE_RE.search(s)
                if match:
                    row["effective_date"] = apply_defined_dates(trim_effective(match.group(1)), defined)
                    break

    # Swap any leftover "Mr. Parekh" for a full name found later in the section.
    for row in events.values():
        row["person_name"] = resolve_name(row["person_name"], known_names) \
            if re.match(HONORIFIC, row["person_name"]) else row["person_name"]
    return list(events.values())


# ---------------------------------------------------------------------------
# Main pipeline: loop over companies and filings, print events, save CSV
# ---------------------------------------------------------------------------

def process_filing(company, filing):
    """Return the list of event rows for one filing, or None if it failed."""
    ticker = company["ticker"]
    date = filing["filing_date"]
    url = filing_url(company["cik"], filing["accession"], filing["primary_document"])

    try:
        text = html_to_text(sec_get(url).text)
    except requests.RequestException as err:
        print(f"WARNING [{ticker}] {date}: 8-K download failed ({err}), skipping")
        return None

    section = item_502_section(text)
    rows = []
    for event in extract_events(section):
        row = {"company": company["company"], "ticker": ticker,
               "cik": company["cik"], "filing_date": date, **event}
        # Guarantee no blank or None cells: missing data is "NOT_FOUND".
        for col in CSV_COLUMNS:
            if row.get(col) in (None, ""):
                row[col] = NOT_FOUND
        rows.append(row)
    return rows


def print_row(row):
    """Print in the required format: [Ticker] | [Date] | [Event Type] | [Name] | [Title]"""
    print(f"{row['ticker']} | {row['filing_date']} | {row['event_type']} | "
          f"{row['person_name']} | {row['title']}")


def main():
    today = datetime.date.today()
    cutoff = one_year_ago(today)
    print(f"Looking for 8-K Item 5.02 filings from {cutoff} to {today}")
    rows = []

    for company in COMPANIES:
        ticker = company["ticker"]
        print(f"\n=== {company['company']} ({ticker}) ===")

        try:
            filings = get_executive_filings(company["cik"], cutoff)
        except (requests.RequestException, ValueError, KeyError) as err:
            print(f"WARNING [{ticker}]: could not load EDGAR submissions ({err}), skipping company")
            continue

        # Zero filings is a finding, not an error.
        if not filings:
            print(f"{ticker}: No executive events in past 12 months")
            continue

        for filing in filings:
            try:
                events = process_filing(company, filing)
            except Exception as err:  # never let one bad filing crash the run
                print(f"WARNING [{ticker}] {filing['filing_date']}: could not parse filing ({err}), skipping")
                continue
            if events is None:
                continue
            if not events:
                # e.g. a 5.02(e) filing that only approves a compensation plan
                print(f"{ticker} | {filing['filing_date']} | no departure or appointment found "
                      f"in Item 5.02 (likely compensation-only)")
                continue
            for row in events:
                print_row(row)
                rows.append(row)

    # Step 7: save all rows to CSV (header only if there were no events)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} rows to {os.path.relpath(OUTPUT_CSV)}")


if __name__ == "__main__":
    main()
