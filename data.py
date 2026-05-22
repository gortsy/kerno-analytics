# data.py — fetches real SEC filing text for accurate analysis
# Drop this into your kerno folder, replacing the existing data.py

import re
import logging
import requests

log = logging.getLogger("kerno.data")

HEADERS   = {"User-Agent": "Kerno Analytics contact@kerno.io"}
TICKER_RE = re.compile(r'^[A-Z]{1,6}$')

# Target these SEC filing sections — they contain the actual numbers
FINANCIAL_SECTIONS = [
    "results of operations",
    "consolidated statements of operations",
    "consolidated statements of income",
    "condensed consolidated statements",
    "revenue",
    "net income",
    "earnings per share",
    "gross profit",
    "operating income",
    "liquidity and capital",
    "outlook",
    "guidance",
    "financial highlights",
    "management",
]


# ── Input validation ────────────────────────────────────────────────────────
def validate_ticker(ticker: str) -> str:
    if not ticker or not isinstance(ticker, str):
        return ""
    t = re.sub(r'[^A-Z]', '', ticker.upper().strip())[:6]
    return t if TICKER_RE.match(t) else ""


# ── SEC helpers ─────────────────────────────────────────────────────────────
def get_cik(ticker: str):
    try:
        r = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=HEADERS, timeout=10
        )
        r.raise_for_status()
        for entry in r.json().values():
            if entry.get("ticker", "").upper() == ticker:
                cik  = str(entry["cik_str"]).zfill(10)
                name = entry.get("title") or entry.get("name") or ticker
                return cik, name
        return None, f"Ticker '{ticker}' not found in SEC database."
    except requests.exceptions.Timeout:
        return None, "SEC EDGAR timed out. Try again."
    except Exception as e:
        return None, f"Error looking up ticker: {e}"


def get_latest_filing(cik: str):
    try:
        r = requests.get(
            f"https://data.sec.gov/submissions/CIK{cik}.json",
            headers=HEADERS, timeout=10
        )
        r.raise_for_status()
        data         = r.json()
        filings      = data.get("filings", {}).get("recent", {})
        forms        = filings.get("form", [])
        dates        = filings.get("filingDate", [])
        accessions   = filings.get("accessionNumber", [])
        primary_docs = filings.get("primaryDocument", [])

        for i, form in enumerate(forms):
            if form in ("10-Q", "10-K"):
                acc_fmt     = accessions[i].replace("-", "")
                primary_doc = primary_docs[i] if i < len(primary_docs) else ""
                cik_int     = int(cik)
                return {
                    "form":        form,
                    "date":        dates[i],
                    "accession":   accessions[i],
                    "viewer_url":  (
                        f"https://www.sec.gov/cgi-bin/browse-edgar"
                        f"?action=getcompany&CIK={cik}&type={form}"
                        f"&dateb=&owner=include&count=1"
                    ),
                    "filing_url":  (
                        f"https://www.sec.gov/Archives/edgar/data/"
                        f"{cik_int}/{acc_fmt}/{primary_doc}"
                    ),
                    "index_url":   (
                        f"https://www.sec.gov/Archives/edgar/data/"
                        f"{cik_int}/{acc_fmt}/"
                    ),
                }, None

        return None, "No 10-Q or 10-K found for this company."

    except requests.exceptions.Timeout:
        return None, "SEC EDGAR timed out. Try again."
    except Exception as e:
        return None, f"Error fetching filing: {e}"


def get_filing_documents(index_url: str) -> list[dict]:
    """
    Fetch the filing index page and return a list of documents.
    We want to find the main financial document, not just the primary doc.
    """
    try:
        # Convert index URL to the JSON version
        json_url = index_url.rstrip("/") + "/index.json"
        r = requests.get(json_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        docs = data.get("directory", {}).get("item", [])
        return docs
    except Exception:
        return []


def find_best_document(docs: list, index_url: str) -> str:
    """
    From the filing document list, find the URL of the main financial document.
    Prefers .htm files over .txt, and avoids exhibit files.
    """
    base = index_url.rstrip("/")
    candidates = []

    for doc in docs:
        name = doc.get("name", "").lower()
        # Skip exhibits, graphics, CSS, JS
        if any(x in name for x in ["ex", "exhibit", ".gif", ".jpg", ".css", ".js", "R1.", "R2."]):
            continue
        if name.endswith(".htm") or name.endswith(".html"):
            candidates.append(doc.get("name", ""))

    # Prefer shorter filenames — usually the main document
    if candidates:
        candidates.sort(key=len)
        return f"{base}/{candidates[0]}"

    return ""


def clean_html(html: str) -> str:
    """Strip HTML and normalize whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = (text
        .replace("&nbsp;", " ").replace("&amp;", "&")
        .replace("&lt;",   "<").replace("&gt;",  ">")
        .replace("&#160;", " ").replace("&quot;", '"')
        .replace("\xa0",   " "))
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_key_sections(text: str, max_chars: int = 14000) -> str:
    """
    Find and extract the most financially relevant sections of the filing.
    Returns up to max_chars of the most useful content.
    """
    lines  = text.split("\n")
    result = []
    in_section = False
    chars_collected = 0
    section_buffer = []
    section_chars  = 0

    i = 0
    while i < len(lines) and chars_collected < max_chars:
        line      = lines[i].strip()
        line_low  = line.lower()
        i += 1

        if not line:
            if in_section and section_buffer:
                section_buffer.append("")
                section_chars += 1
            continue

        # Check if this line starts a target section
        is_section_header = any(s in line_low for s in FINANCIAL_SECTIONS)

        if is_section_header and len(line) < 120:
            # Save previous section if it had content
            if section_buffer and section_chars > 50:
                result.extend(section_buffer)
                chars_collected += section_chars

            section_buffer = [line, ""]
            section_chars  = len(line) + 1
            in_section     = True
            continue

        if in_section:
            # Stop collecting if we hit a new major section that's not financial
            if (len(line) < 80 and line.isupper() and
                    not any(s in line_low for s in FINANCIAL_SECTIONS)):
                if section_chars > 200:
                    result.extend(section_buffer)
                    chars_collected += section_chars
                in_section    = False
                section_buffer = []
                section_chars  = 0
                continue

            # Collect lines with numbers — they have the actual data
            has_number = bool(re.search(r'\d', line))
            has_dollar = bool(re.search(r'\$|\bmillion\b|\bbillion\b', line_low))
            has_pct    = bool(re.search(r'\d+\.?\d*\s*%', line))

            if has_number or has_dollar or has_pct or len(section_buffer) < 5:
                section_buffer.append(line)
                section_chars += len(line) + 1

            # Cap each section at 3000 chars
            if section_chars >= 3000:
                result.extend(section_buffer)
                chars_collected += section_chars
                in_section    = False
                section_buffer = []
                section_chars  = 0

    # Flush remaining section
    if section_buffer and section_chars > 50:
        result.extend(section_buffer)

    return "\n".join(result)[:max_chars]


def get_filing_text(filing_url: str, index_url: str = "") -> str:
    """
    Fetch the filing and extract the key financial sections.
    Falls back gracefully at every step.
    """
    # Try to find a better document from the filing index
    best_url = filing_url
    if index_url:
        docs = get_filing_documents(index_url)
        if docs:
            better = find_best_document(docs, index_url)
            if better:
                best_url = better
                log.info(f"Using document: {best_url}")

    # Fetch the document
    for url in [best_url, filing_url]:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            raw_text = r.text
            break
        except Exception as e:
            log.warning(f"Could not fetch {url}: {e}")
            raw_text = ""

    if not raw_text:
        return ""

    # Clean HTML
    clean = clean_html(raw_text)

    # Extract the financially relevant sections
    extracted = extract_key_sections(clean)

    if extracted:
        log.info(f"Extracted {len(extracted)} chars of financial text")
    else:
        log.warning("No key sections found — using raw text fallback")
        # Fallback: return the first 8000 chars of cleaned text
        extracted = clean[:8000]

    return extracted


# ── Public interface ────────────────────────────────────────────────────────
def lookup_company(ticker: str) -> dict:
    """
    Full pipeline: validate → CIK → filing → financial text extraction.
    Returns a company dict or {"error": "..."}.
    """
    clean = validate_ticker(ticker)
    if not clean:
        return {"error": f"'{ticker}' is not a valid ticker. Must be 1-6 letters."}

    cik, name_or_err = get_cik(clean)
    if cik is None:
        return {"error": name_or_err}

    filing, err = get_latest_filing(cik)
    if filing is None:
        return {"error": err}

    # Fetch real filing text from the actual document
    filing_text = get_filing_text(
        filing_url=filing["filing_url"],
        index_url=filing.get("index_url", "")
    )

    return {
        "ticker":       clean,
        "name":         name_or_err,
        "cik":          cik,
        "form":         filing["form"],
        "date":         filing["date"],
        "accession":    filing.get("accession", ""),
        "viewer_url":   filing["viewer_url"],
        "filing_text":  filing_text,
    }
