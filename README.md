# ⚡ Kerno Analytics

> Find the signal. Skip the noise.

AI-powered earnings call and SEC filing analysis for retail investors.
Built by Grant Stubblefield — Oregon State University, 2026.

---

## What it does

Type any US stock ticker → Kerno pulls the latest 10-Q or 10-K from SEC EDGAR,
sends it to Google Gemini, and returns a structured analysis in under 30 seconds:

- 3-second take
- 3 key signal metrics with direction
- Key signals from the filing
- Management tone observations
- Risks to watch
- Bottom line (bull case + main risk)

---

## File structure

```
kerno/
├── app.py              ← Main Streamlit app (run this)
├── data.py             ← SEC EDGAR data fetching
├── analyze.py          ← Google Gemini AI analysis
├── requirements.txt    ← Python dependencies
├── .env.example        ← Copy to .env and add your key
├── .gitignore          ← Keeps secrets out of git
└── .streamlit/
    └── config.toml     ← Streamlit theme config
```

---

## Setup — step by step

### Step 1 — Get your Google AI Studio API key (free)

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click **Create API key**
4. Copy the key — you'll need it in Step 3

Free tier: 1,500 requests/day, 1M tokens/minute. More than enough.

---

### Step 2 — Set up your project folder

Open Terminal (Mac) or Command Prompt (Windows) and run:

```bash
# Create and enter the project folder
mkdir kerno && cd kerno

# Create a virtual environment
python -m venv venv

# Activate it
source venv/bin/activate        # Mac / Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

---

### Step 3 — Add your API key

```bash
# Copy the example env file
cp .env.example .env
```

Open `.env` in any text editor and replace the placeholder:

```
GOOGLE_API_KEY=your_actual_key_here
```

Save the file. Never commit `.env` to git — it's already in `.gitignore`.

---

### Step 4 — Run locally

```bash
streamlit run app.py
```

Your browser opens automatically at http://localhost:8501.
Type any ticker (AAPL, NVDA, MSFT...) and hit Analyze.

---

## Deploy free on Streamlit Cloud

Streamlit Cloud hosts your app for free with a public URL.

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "initial kerno build"

# Create a repo on github.com first, then:
git remote add origin https://github.com/YOUR_USERNAME/kerno-analytics.git
git push -u origin main
```

### Step 2 — Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click **New app**
4. Select your repo → branch: `main` → file: `app.py`
5. Click **Advanced settings**
6. Under **Secrets**, add:
   ```
   GOOGLE_API_KEY = "your_key_here"
   ```
7. Click **Deploy**

Your live URL will be: `https://your-username-kerno-analytics-app-xxxx.streamlit.app`

Takes about 2 minutes. Free forever on the Streamlit Community plan.

---

## Cost

| Resource | Cost |
|----------|------|
| Google Gemini 1.5 Flash | Free (1,500 req/day) |
| SEC EDGAR data | Free (always) |
| Streamlit Cloud hosting | Free |
| Total to run Kerno | $0 |

---

## Tech stack

- **Python 3.11+**
- **Streamlit** — web UI
- **Google Gemini 1.5 Flash** — AI analysis
- **SEC EDGAR API** — real-time filing data (free, no key needed)
- **python-dotenv** — environment variable management

---

## Roadmap

- [ ] Historical QoQ comparison (Q1 vs Q2 vs Q3)
- [ ] Email alerts when a tracked company files
- [ ] Actual transcript text from earnings calls
- [ ] Portfolio watchlist with saved analyses
- [ ] Export to PDF

---

## Disclaimer

Kerno Analytics is for informational purposes only.
Nothing here is financial advice. Always do your own research.

---

Built by Grant Stubblefield · Oregon State University · 2026
