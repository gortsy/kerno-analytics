# analyze.py — pulls real numbers directly from SEC filings
# Drop this into your kerno folder, replacing the existing analyze.py

import os
import re
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("kerno.analyze")

# ── Config ──────────────────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "models/gemini-3.5-flash")

if not GOOGLE_API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY not found. "
        "Make sure your .env file contains GOOGLE_API_KEY=your_key_here"
    )

genai.configure(api_key=GOOGLE_API_KEY)


# ── Number extractor ────────────────────────────────────────────────────────
def extract_financials(text: str) -> str:
    """
    Pre-process the raw filing text to pull out the most number-dense
    sections before sending to Gemini. This dramatically improves
    accuracy because Gemini sees the actual figures, not prose.
    """
    if not text:
        return ""

    lines = text.split("\n")
    scored = []

    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue

        score = 0

        # Lines with dollar amounts
        if re.search(r'\$[\d,]+', line):
            score += 3
        # Lines with numbers (could be millions/billions)
        if re.search(r'\b\d{1,3}(?:,\d{3})+\b', line):
            score += 2
        # Lines with percentages
        if re.search(r'\d+\.?\d*\s*%', line):
            score += 2
        # Financial keywords
        keywords = [
            'revenue', 'income', 'earnings', 'margin', 'profit', 'loss',
            'cash', 'operating', 'net', 'gross', 'diluted', 'eps',
            'quarter', 'year', 'growth', 'increase', 'decrease',
            'guidance', 'outlook', 'forecast', 'expect', 'billion', 'million'
        ]
        for kw in keywords:
            if kw in line.lower():
                score += 1

        if score >= 3:
            scored.append((score, line))

    # Sort by score descending, take the top lines
    scored.sort(key=lambda x: x[0], reverse=True)
    top_lines = [line for _, line in scored[:80]]

    # Return in original order (re-sort by position)
    result = []
    for line in lines:
        if line.strip() in top_lines:
            result.append(line.strip())

    return "\n".join(result[:80])


# ── Prompt ──────────────────────────────────────────────────────────────────
def build_prompt(company: dict) -> str:
    raw_text     = company.get("filing_text", "")
    key_sections = extract_financials(raw_text)

    if key_sections:
        text_block = f"""
The following lines were extracted directly from the {company['form']} filing.
These contain the actual financial figures — USE THESE NUMBERS EXACTLY as reported.
Do not round, estimate, or substitute figures from memory.

--- FILING EXTRACT START ---
{key_sections}
--- FILING EXTRACT END ---
"""
    else:
        text_block = """
No filing text was available. Use your training knowledge for this company's
most recently reported quarter, and note in three_second_take that figures
are estimates based on training data.
"""

    return f"""You are a senior equity research analyst reading a real SEC filing.

Company: {company['name']} (ticker: {company['ticker']})
Filing:  {company['form']} · {company['date']}

{text_block}

STRICT RULES:
1. If filing text was provided above, use ONLY those numbers — do not substitute from memory.
2. If a figure is not in the extract, write "not disclosed" — never estimate.
3. Keep every string value under 100 characters.
4. metric_dir must be exactly: up, down, or neutral — nothing else.
5. Return ONLY the JSON object below. No markdown, no fences, no text before {{ or after }}.

{{
  "three_second_take": "One sentence capturing the most important thing about this quarter",
  "metric1_label": "most important top-line metric label e.g. Revenue",
  "metric1_value": "exact value from filing e.g. $44.9B",
  "metric1_change": "YoY or QoQ change with comparison e.g. +9% vs $41.3B prior year",
  "metric1_dir": "up",
  "metric2_label": "second most important metric e.g. Net Income",
  "metric2_value": "exact value from filing",
  "metric2_change": "change with comparison",
  "metric2_dir": "up",
  "metric3_label": "third metric e.g. Gross Margin or key segment",
  "metric3_value": "exact value from filing",
  "metric3_change": "change with comparison",
  "metric3_dir": "neutral",
  "key_signals": [
    "Specific finding with exact number from filing",
    "Specific finding with exact number from filing",
    "Specific finding with exact number from filing",
    "Specific finding with exact number from filing"
  ],
  "management_tone": [
    "Direct quote or close paraphrase from management language in filing",
    "Specific forward guidance statement or outlook language from filing"
  ],
  "risks": [
    "Specific risk factor mentioned in this filing — not generic",
    "Second specific risk factor from this filing"
  ],
  "bottom_line": "Bull case in one sentence with a real number. Key risk in one sentence."
}}
"""


# ── JSON repair ─────────────────────────────────────────────────────────────
def repair_json(raw: str) -> dict:
    start = raw.find("{")
    if start == -1:
        raise ValueError("No JSON object in Gemini response")
    raw = raw[start:]

    for attempt in [raw, raw + "}", raw + '"]}']:
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            pass

    # Regex fallback
    result = {}
    for m in re.finditer(r'"(\w+)"\s*:\s*"([^"]*)"', raw):
        result[m.group(1)] = m.group(2)
    for m in re.finditer(r'"(\w+)"\s*:\s*\[([^\]]*)\]', raw):
        result[m.group(1)] = re.findall(r'"([^"]*)"', m.group(2))

    if len(result) >= 4:
        log.warning("Used regex fallback to parse Gemini response")
        return result

    raise ValueError(f"Could not parse response. Raw (first 300 chars): {raw[:300]}")


# ── Sanitizer ───────────────────────────────────────────────────────────────
def sanitize(value):
    if isinstance(value, str):
        return re.sub(r"<[^>]+>", "", value).strip()
    if isinstance(value, list):
        return [sanitize(i) for i in value]
    return value


# ── Main ─────────────────────────────────────────────────────────────────────
def analyze(company: dict) -> dict:
    """
    Takes a company dict from data.lookup_company() and returns
    a structured analysis dict with figures sourced from the actual filing.
    Raises RuntimeError on failure.
    """
    if not isinstance(company, dict):
        raise RuntimeError("Invalid company data passed to analyze()")
    if "error" in company:
        raise RuntimeError(f"Company lookup failed: {company['error']}")
    if not company.get("ticker"):
        raise RuntimeError("Company data missing ticker field")

    ticker = company["ticker"]
    has_text = bool(company.get("filing_text"))
    log.info(f"Analyzing {ticker} — filing text available: {has_text}")

    try:
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            generation_config=genai.GenerationConfig(
                temperature=0,        # fully deterministic
                max_output_tokens=8192,
            )
        )

        prompt   = build_prompt(company)
        response = model.generate_content(prompt)
        raw      = response.text.strip()

        # Strip markdown fences if present
        raw = re.sub(r"```json?", "", raw).replace("```", "").strip()

        result = repair_json(raw)

        # Sanitize all output fields
        clean = {k: sanitize(v) for k, v in result.items()}

        # Tag whether this came from real filing data or training knowledge
        clean["sourced_from_filing"] = has_text

        return clean

    except RuntimeError:
        raise
    except Exception as e:
        log.error(f"Gemini error for {ticker}: {e}")
        raise RuntimeError(
            f"AI analysis failed: {str(e)}\n\n"
            "Check that GOOGLE_API_KEY is correct in your .env file."
        )
