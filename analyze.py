# analyze.py — hardened version
# Replaces your existing analyze.py — drop this in your kerno folder

import os
import re
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("kerno.analyze")

# ── Config ─────────────────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "models/gemini-3.5-flash")

if not GOOGLE_API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY not found. "
        "Make sure your .env file exists and contains GOOGLE_API_KEY=your_key_here"
    )

genai.configure(api_key=GOOGLE_API_KEY)

# ── Prompt ─────────────────────────────────────────────────────────────────
def build_prompt(company: dict) -> str:
    text_block = (
        f"\n\nFiling text (truncated):\n\n{company['filing_text'][:6000]}"
        if company.get("filing_text")
        else "\n\nUse your training knowledge of this company's most recent results."
    )
    return f"""You are a senior equity research analyst at a top-tier investment bank.
Analyze {company['name']} (ticker: {company['ticker']}).
Filing: {company['form']} filed on {company['date']}.
{text_block}

Return ONLY a raw JSON object. No markdown, no code fences, nothing before {{ or after }}.
Keep every string value under 100 characters.

{{
  "three_second_take": "One punchy sentence under 90 chars",
  "metric1_label": "e.g. Revenue YoY",
  "metric1_value": "e.g. +18.3%",
  "metric1_change": "Short context under 60 chars",
  "metric1_dir": "up",
  "metric2_label": "e.g. Net Income",
  "metric2_value": "$24.2B",
  "metric2_change": "Short context under 60 chars",
  "metric2_dir": "up",
  "metric3_label": "e.g. Gross Margin",
  "metric3_value": "46.2%",
  "metric3_change": "Short context under 60 chars",
  "metric3_dir": "neutral",
  "key_signals": ["Signal with real number", "Signal", "Signal", "Signal"],
  "management_tone": ["Tone observation under 100 chars", "Guidance note under 100 chars"],
  "risks": ["Primary risk — specific", "Secondary risk — specific"],
  "bottom_line": "Bull case sentence. Key risk sentence. Under 200 chars total."
}}

metric_dir must be exactly one of: up, down, neutral
Use real numbers wherever possible.
"""

# ── JSON repair ─────────────────────────────────────────────────────────────
def repair_json(raw: str) -> dict:
    """Try multiple strategies to extract valid JSON from a potentially truncated response."""
    # Find the opening brace
    start = raw.find("{")
    if start == -1:
        raise ValueError("No JSON object found in Gemini response")
    raw = raw[start:]

    # Strategy 1 — parse as-is
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategy 2 — add missing closing brace
    try:
        return json.loads(raw + "}")
    except json.JSONDecodeError:
        pass

    # Strategy 3 — close an open string then close the object
    try:
        return json.loads(raw + '"]}')
    except json.JSONDecodeError:
        pass

    # Strategy 4 — regex extraction of every key-value pair we can find
    result = {}
    for m in re.finditer(r'"(\w+)"\s*:\s*"([^"]*)"', raw):
        result[m.group(1)] = m.group(2)
    for m in re.finditer(r'"(\w+)"\s*:\s*\[([^\]]*)\]', raw):
        result[m.group(1)] = re.findall(r'"([^"]*)"', m.group(2))

    if len(result) >= 4:
        log.warning("Used regex fallback to parse Gemini response")
        return result

    raise ValueError(f"Could not parse Gemini response. Raw (first 300): {raw[:300]}")

# ── Output sanitizer ────────────────────────────────────────────────────────
def sanitize(value):
    """Strip any HTML tags from AI output — safety net against prompt injection."""
    if isinstance(value, str):
        return re.sub(r"<[^>]+>", "", value).strip()
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value

# ── Main analysis function ──────────────────────────────────────────────────
def analyze(company: dict) -> dict:
    """
    Takes a company dict from data.lookup_company() and returns
    a structured, sanitized analysis dict.
    Raises RuntimeError on unrecoverable failure.
    """
    # Validate input
    if not isinstance(company, dict):
        raise RuntimeError("Invalid company data passed to analyze()")
    if "error" in company:
        raise RuntimeError(f"Company lookup failed: {company['error']}")
    if not company.get("ticker"):
        raise RuntimeError("Company data missing ticker field")

    ticker = company["ticker"]
    log.info(f"Running analysis for {ticker}")

    try:
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=8192,
            )
        )

        prompt   = build_prompt(company)
        response = model.generate_content(prompt)
        raw      = response.text.strip()

        # Strip markdown fences if present
        raw = re.sub(r"```json?", "", raw).replace("```", "").strip()

        # Parse
        result = repair_json(raw)

        # Sanitize every field before returning
        return {k: sanitize(v) for k, v in result.items()}

    except RuntimeError:
        raise
    except Exception as e:
        log.error(f"Gemini error for {ticker}: {e}")
        raise RuntimeError(
            f"AI analysis failed: {str(e)}\n\n"
            "Check that GOOGLE_API_KEY is set correctly in your .env file "
            "and that you have quota remaining."
        )
