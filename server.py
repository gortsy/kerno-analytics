import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai

# Load hidden API keys from .env
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configure Gemini Client
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

app = Flask(__name__)
CORS(app) # Allows your local HTML file to communicate with this server

@app.route('/api/analyze', methods=['POST'])
def analyze_ticker():
    data = request.get_json()
    ticker = data.get('ticker', '').upper().strip()
    
    if not ticker:
        return jsonify({"error": "No ticker provided"}), 400

    # The exact engineering prompt from your HTML file
    prompt = f"""
    You are a senior equity research analyst.
    Analyze the stock ticker: {ticker}

    Based on the company's most recent SEC filing and earnings results, return ONLY a valid JSON object.
    No markdown, no code fences, no text before or after. Start with {{ and end with }}.
    Keep every string value under 100 characters.

    {{
      "company_name": "Full legal company name",
      "form_type": "10-Q or 10-K",
      "filing_date": "e.g. Q2 2025",
      "three_second_take": "One punchy sentence under 90 chars",
      "metric1_label": "e.g. Revenue YoY",
      "metric1_value": "e.g. +18.3%",
      "metric1_change": "Short context e.g. $94.9B vs $80.4B prior year",
      "metric1_dir": "up",
      "metric2_label": "e.g. Net Income",
      "metric2_value": "$24.2B",
      "metric2_change": "Short context",
      "metric2_dir": "up",
      "metric3_label": "e.g. Gross Margin",
      "metric3_value": "46.2%",
      "metric3_change": "Short context",
      "metric3_dir": "neutral",
      "key_signals": ["Signal with number", "Signal with number", "Signal with number", "Signal with number"],
      "management_tone": ["Tone observation", "Guidance note"],
      "risks": ["Primary risk — specific", "Secondary risk — specific"],
      "bottom_line": "2 sentences. Bull case then key risk. Under 180 chars.",
      "viewer_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-Q&dateb=&owner=include&count=1"
    }}

    metric_dir must be exactly: up, down, or neutral
    If {ticker} is not a real US-listed company return: {{"error": "not found"}}
    """

    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        # Strip any accidental markdown backticks formatting if Gemini adds them
        if raw_text.startswith("```"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            
        return raw_text, 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        return jsonify({"error": f"Backend processing error: {str(e)}"}), 500

if __name__ == '__main__':
    # Runs a local server at http://localhost:5000
    app.run(port=5000, debug=True)
