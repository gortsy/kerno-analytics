# data.py — hardened version
# Replaces your existing data.py — drop this in your kerno folder

import re
import logging
import requests

log = logging.getLogger("kerno.data")

HEADERS  = {"User-Agent": "Kerno Analytics contact@kerno.io"}
TICKER_RE = re.compile(r'^[A-Z]{1,6}$')

# ── Validation ──────────────────────────────────────────────────────────────
def validate_ticker(ticker: str) -> str:
    """Sanitize and validate ticker format before any network call."""
    if not ticker or not isinstance(ticker, str):
        return ""
    t = re.sub(r'[^A-Z]', '', ticker.upper().strip())[:6]
    if not TICKER_RE.match(t):
        return ""
    return t

# ── SEC helpers ─────────────────────────────────────────────────────────────
def get_cik(ticker: str):
    """Return (cik, company_name) or (None, error_message)."""
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
        return None, "SEC EDGAR timed out. Try again in a moment."
    except requests.exceptions.RequestException as e:
        return None, f"Network error reaching SEC EDGAR: {e}"
    except Exception as e:
        return None, f"Unexpected error looking up ticker: {e}"


def get_latest_filing(cik: str):
    """Return (filing_dict, None) or (None, error_message)."""
    try:
        r = requests.get(
            f"https://data.sec.gov/submissions/CIK{cik}.json",
            headers=HEADERS, timeout=10
        )
        r.raise_for_status()
        data     = r.json()
        filings  = data.get("filings", {}).get("recent", {})
        forms    = filings.get("form", [])
        dates    = filings.get("filingDate", [])
        accessions   = filings.get("accessionNumber", [])
        primary_docs = filings.get("primaryDocument", [])

        for i, form in enumerate(forms):
            if form in ("10-Q", "10-K"):
                acc_fmt     = accessions[i].replace("-", "")
                primary_doc = primary_docs[i] if i < len(primary_docs) else ""
                cik_int     = int(cik)
                return {
                    "form":       form,
                    "date":       dates[i],
                    "viewer_url": (
                        f"https://www.sec.gov/cgi-bin/browse-edgar"
                        f"?action=getcompany&CIK={cik}&type={form}"
                        f"&dateb=&owner=include&count=1"
                    ),
                    "filing_url": (
                        f"https://www.sec.gov/Archives/edgar/data/"
                        f"{cik_int}/{acc_fmt}/{primary_doc}"
                    ),
                }, None

        return None, "No 10-Q or 10-K filing found for this company."

    except requests.exceptions.Timeout:
        return None, "SEC EDGAR timed out fetching the filing. Try again."
    except requests.exceptions.RequestException as e:
        return None, f"Network error fetching filing: {e}"
    except Exception as e:
        return None, f"Unexpected error fetching filing: {e}"


def get_filing_text(filing_url: str, max_chars: int = 6000) -> str:
    """Download and clean filing HTML. Returns empty string on any failure."""
    try:
        r = requests.get(filing_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        text = r.text

        # Strip HTML
        text = re.sub(r"<[^>]+>", " ", text)
        # Decode common entities
        text = (text
            .replace("&nbsp;", " ").replace("&amp;", "&")
            .replace("&lt;",   "<").replace("&gt;",  ">")
            .replace("&#160;", " ").replace("&quot;", '"'))
        # Collapse whitespace
        text = re.sub(r"\s{3,}", "\n\n", text).strip()

        return text[:max_chars]

    except Exception as e:
        log.warning(f"Could not fetch filing text from {filing_url}: {e}")
        return ""  # graceful fallback — AI uses training knowledge


# ── Public interface ────────────────────────────────────────────────────────
def lookup_company(ticker: str) -> dict:
    """
    Full pipeline: validate → CIK lookup → filing metadata → filing text.
    Returns a company dict, or {"error": "..."} on failure.
    """
    # Validate first — never hit the network with dirty input
    clean = validate_ticker(ticker)
    if not clean:
        return {"error": f"'{ticker}' is not a valid ticker format. Must be 1-6 letters."}

    cik, name_or_err = get_cik(clean)
    if cik is None:
        return {"error": name_or_err}

    filing, err = get_latest_filing(cik)
    if filing is None:
        return {"error": err}

    filing_text = get_filing_text(filing["filing_url"])

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
