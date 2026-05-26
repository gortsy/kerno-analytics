# kerno/app.py
import html

import streamlit as st
from data import lookup_company
from analyze import analyze

import logging
logging.basicConfig(level=logging.INFO)

if "analysis_cache" not in st.session_state:
    st.session_state["analysis_cache"] = {}

st.set_page_config(
    page_title="Kerno Analytics",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');
  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
  .stApp { background: #080a0f; color: #e8ecf4; }
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 760px; }

  .hero-tag  { font-family: 'DM Mono', monospace; font-size: 11px; color: #4f8eff;
               letter-spacing: .1em; text-transform: uppercase; margin-bottom: 8px; }
  .hero-h1   { font-size: 2.6rem; font-weight: 500; line-height: 1.1;
               color: #e8ecf4; margin-bottom: 12px; }
  .hero-h1 em { color: #4f8eff; font-style: italic; }
  .hero-sub  { font-size: 1rem; color: #6b7a99; font-weight: 300;
               line-height: 1.7; margin-bottom: 0; }

  .stTextInput > div > div > input {
    background: #161b27 !important;
    border: 1px solid #2a3347 !important;
    border-radius: 8px !important;
    color: #e8ecf4 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 1rem !important;
    letter-spacing: .08em !important;
    padding: 14px 18px !important;
  }
  .stTextInput > div > div > input:focus {
    border-color: #4f8eff !important;
    box-shadow: 0 0 0 2px rgba(79,142,255,.15) !important;
  }
  .stButton > button {
    background: #4f8eff !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: .8rem !important;
    font-weight: 500 !important;
    letter-spacing: .06em !important;
    padding: 10px 22px !important;
    transition: background .2s !important;
    width: 100% !important;
  }
  .stButton > button:hover { background: #2563eb !important; }

  .result-window {
    background: #0d1018; border: 0.5px solid #2a3347;
    border-radius: 12px; overflow: hidden; margin-top: 24px;
  }
  .result-titlebar {
    background: #161b27; padding: 10px 18px;
    display: flex; align-items: center; gap: 8px;
    border-bottom: 0.5px solid #1e2535;
  }
  .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
  .dot-r { background: #ff5f57; } .dot-a { background: #febc2e; } .dot-g { background: #28c840; }
  .url-bar { flex: 1; text-align: center; font-family: 'DM Mono', monospace;
             font-size: 11px; color: #3a4560; letter-spacing: .04em; }
  .result-body { padding: 24px; }

  .take-box { background: rgba(79,142,255,.08); border: 0.5px solid rgba(79,142,255,.25);
              border-radius: 8px; padding: 14px 18px; margin-bottom: 20px;
              font-size: .95rem; color: #e8ecf4; line-height: 1.6; }
  .take-label { font-family: 'DM Mono', monospace; font-size: 10px; color: #4f8eff;
                letter-spacing: .1em; text-transform: uppercase; margin-bottom: 6px; }

  .metric-row { display: flex; gap: 10px; margin-bottom: 20px; }
  .metric-card { flex: 1; background: #12151e; border: 0.5px solid #2a3347;
                 border-radius: 8px; padding: 14px; }
  .metric-label { font-family: 'DM Mono', monospace; font-size: 9px; color: #6b7a99;
                  letter-spacing: .08em; text-transform: uppercase; margin-bottom: 5px; }
  .metric-value { font-family: 'DM Mono', monospace; font-size: 1.25rem; font-weight: 500; }
  .metric-change { font-size: .72rem; color: #6b7a99; margin-top: 2px; }
  .up { color: #22d47a; } .down { color: #ff4f6a; } .neutral { color: #e8ecf4; }

  .insight-block { margin-bottom: 18px; }
  .insight-title { font-family: 'DM Mono', monospace; font-size: 10px; color: #4f8eff;
                   letter-spacing: .08em; text-transform: uppercase; margin-bottom: 10px;
                   border-left: 3px solid #4f8eff; padding-left: 10px; }
  .insight-item { font-size: .87rem; color: #6b7a99; padding: 7px 0;
                  border-bottom: 0.5px solid #1e2535; line-height: 1.55; }
  .insight-item:last-child { border-bottom: none; }
  .arrow { color: #4f8eff; font-family: 'DM Mono', monospace;
           font-size: .75rem; margin-right: 8px; }

  .bottom-line { background: rgba(34,212,122,.06); border: 0.5px solid rgba(34,212,122,.2);
                 border-radius: 8px; padding: 16px; margin-top: 4px; }
  .bl-label { font-family: 'DM Mono', monospace; font-size: 10px; color: #22d47a;
              letter-spacing: .1em; text-transform: uppercase; margin-bottom: 6px; }
  .bl-text { font-size: .87rem; color: #6b7a99; line-height: 1.65; }

  .filing-link { font-family: 'DM Mono', monospace; font-size: 11px; color: #3a4560;
                 margin-top: 16px; padding-top: 14px; border-top: 0.5px solid #1e2535; }
  .filing-link a { color: #4f8eff; text-decoration: none; }

  .error-box { background: rgba(255,79,106,.06); border: 0.5px solid rgba(255,79,106,.25);
               border-radius: 8px; padding: 18px; margin-top: 16px; text-align: center; }
  .error-title { font-family: 'DM Mono', monospace; font-size: .85rem;
                 color: #ff4f6a; margin-bottom: 6px; }
  .error-sub { font-size: .82rem; color: #6b7a99; line-height: 1.6; }

  hr { border-color: #1e2535 !important; }
  .footer { font-family: 'DM Mono', monospace; font-size: 11px; color: #3a4560;
             text-align: center; margin-top: 40px; }
</style>
""", unsafe_allow_html=True)


def dir_class(d):
    return {"up": "up", "down": "down"}.get(str(d).lower(), "neutral")


def esc(value):
    return html.escape(str(value or ""), quote=True)


def render_result(company, analysis):
    company = {k: esc(v) for k, v in company.items()}
    analysis = {
        k: [esc(item) for item in v] if isinstance(v, list) else esc(v)
        for k, v in analysis.items()
    }
    signals_html = "".join(
        f'<div class="insight-item"><span class="arrow">→</span>{s}</div>'
        for s in analysis.get("key_signals", [])
    )
    tone_html = "".join(
        f'<div class="insight-item"><span class="arrow">→</span>{s}</div>'
        for s in analysis.get("management_tone", [])
    )
    risks_html = "".join(
        f'<div class="insight-item"><span class="arrow">→</span>{s}</div>'
        for s in analysis.get("risks", [])
    )
    m1c = dir_class(analysis.get("metric1_dir", ""))
    m2c = dir_class(analysis.get("metric2_dir", ""))
    m3c = dir_class(analysis.get("metric3_dir", ""))

    st.markdown(f"""
    <div class="result-window">
      <div class="result-titlebar">
        <span class="dot dot-r"></span>
        <span class="dot dot-a"></span>
        <span class="dot dot-g"></span>
        <span class="url-bar">kerno.io/analyze/{company['ticker']}</span>
      </div>
      <div class="result-body">
        <div style="margin-bottom:18px;padding-bottom:16px;border-bottom:0.5px solid #1e2535;">
          <div style="font-family:'DM Mono',monospace;font-size:1.2rem;font-weight:500;color:#e8ecf4;margin-bottom:3px;">
            {company['name']} <span style="color:#6b7a99;font-size:.9rem;">/ {company['ticker']}</span>
          </div>
          <div style="font-family:'DM Mono',monospace;font-size:11px;color:#6b7a99;letter-spacing:.04em;">
            {company['form']} · Filed {company['date']} · Analyzed by Kerno AI
          </div>
        </div>
        <div class="take-box">
          <div class="take-label">3-second take</div>
          {analysis.get('three_second_take', '')}
        </div>
        <div class="metric-row">
          <div class="metric-card">
            <div class="metric-label">{analysis.get('metric1_label','')}</div>
            <div class="metric-value {m1c}">{analysis.get('metric1_value','')}</div>
            <div class="metric-change">{analysis.get('metric1_change','')}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">{analysis.get('metric2_label','')}</div>
            <div class="metric-value {m2c}">{analysis.get('metric2_value','')}</div>
            <div class="metric-change">{analysis.get('metric2_change','')}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">{analysis.get('metric3_label','')}</div>
            <div class="metric-value {m3c}">{analysis.get('metric3_value','')}</div>
            <div class="metric-change">{analysis.get('metric3_change','')}</div>
          </div>
        </div>
        <div class="insight-block">
          <div class="insight-title">Key signals</div>
          {signals_html}
        </div>
        <div class="insight-block">
          <div class="insight-title">Management tone</div>
          {tone_html}
        </div>
        <div class="insight-block">
          <div class="insight-title">Risks to watch</div>
          {risks_html}
        </div>
        <div class="bottom-line">
          <div class="bl-label">Bottom line</div>
          <div class="bl-text">{analysis.get('bottom_line','')}</div>
        </div>
        <div class="filing-link">
          Source: <a href="{company['viewer_url']}" target="_blank" rel="noopener noreferrer">
            SEC EDGAR — {company['name']} {company['form']} ({company['date']})
          </a>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Hero ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-tag">// AI-powered financial research</div>
<div class="hero-h1">Find the <em>signal.</em><br>Skip the noise.</div>
<div class="hero-sub">
  Earnings calls. SEC filings. Analyst language.<br>
  Kerno reads it all and surfaces what actually matters — in seconds.
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

# ── Input ────────────────────────────────────────────────────────────────────
# Use a separate key "ticker_input" for the widget.
# Quick-pick buttons write to "pending_ticker" — never touch the widget key directly.
col1, col2 = st.columns([4, 1])
with col1:
    typed = st.text_input(
        label="ticker",
        placeholder="Enter a ticker — AAPL, NVDA, MSFT...",
        label_visibility="collapsed",
        key="ticker_input",
        max_chars=10,
    )
with col2:
    analyze_clicked = st.button("Analyze →", use_container_width=True)

# Quick-pick row
st.markdown('<div style="margin-top:10px;"><span style="font-family:\'DM Mono\',monospace;font-size:11px;color:#3a4560;">Try:</span></div>', unsafe_allow_html=True)

quick_tickers = ["AAPL", "NVDA", "MSFT", "TSLA", "AMZN", "META"]
quick_cols = st.columns(len(quick_tickers))
for i, qt in enumerate(quick_tickers):
    with quick_cols[i]:
        # Write to "pending_ticker" — safe because it's not a widget key
        if st.button(qt, key=f"quick_{qt}"):
            st.session_state["pending_ticker"] = qt

st.markdown("<hr>", unsafe_allow_html=True)

# ── Resolve what ticker to run ───────────────────────────────────────────────
run_ticker = None

if analyze_clicked and typed:
    run_ticker = typed.strip().upper()
elif "pending_ticker" in st.session_state:
    run_ticker = st.session_state.pop("pending_ticker")

# ── Run analysis ─────────────────────────────────────────────────────────────
if run_ticker:
    with st.spinner(f"Pulling {run_ticker} from SEC EDGAR..."):
        company = lookup_company(run_ticker)

    if "error" in company:
        st.markdown(f"""
        <div class="error-box">
          <div class="error-title">Could not find {esc(run_ticker)}</div>
          <div class="error-sub">{esc(company['error'])}</div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()
    else:
        cache_key = f"{company['ticker']}_{company['date']}"

    if cache_key in st.session_state["analysis_cache"]:
        result = st.session_state["analysis_cache"][cache_key]
        st.caption("Loaded from cache - same filing, consistent results")
    else:
        with st.spinner(f"Analyzing {company['name']} with Gemini..."):
            try:
                result = analyze(company)
                if result:
                    st.session_state["analysis_cache"][cache_key] = result
            except RuntimeError as e:
                result = None
                st.markdown(f"""
                <div class="error-box">
                  <div class="error-title">AI analysis failed</div>
                  <div class="error-sub">{esc(e)}</div>
                </div>
                """, unsafe_allow_html=True)

        if result:
            if result.get("sourced_from_filing"):
                st.success("Figures sourced directly from SEC filing")
            else:
                st.warning("Filing text unavailable - figures from AI training knowledge")
            render_result(company, result)

else:
    st.markdown("""
    <div style="text-align:center;padding:48px 0;color:#3a4560;">
      <div style="font-size:2rem;margin-bottom:12px;">⚡</div>
      <div style="font-family:'DM Mono',monospace;font-size:.85rem;margin-bottom:8px;color:#6b7a99;">
        Enter a ticker above to generate a real AI analysis
      </div>
      <div style="font-size:.8rem;color:#3a4560;">
        Powered by Google Gemini · Data from SEC EDGAR · Free to use
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:11px;color:#4f8eff;
                letter-spacing:.08em;text-transform:uppercase;margin-bottom:16px;">
      // About Kerno
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    **Kerno Analytics** surfaces key investment signals from SEC filings and earnings calls —
    making institutional-quality research accessible to everyone.

    Built by **Grant Stubblefield** · Oregon State University · 2026
    """)
    st.markdown("---")
    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:11px;color:#6b7a99;">
    Data: SEC EDGAR (free, real-time)<br>
    AI: Google Gemini 1.5 Flash<br>
    Not financial advice.
    </div>
    """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
  Kerno Analytics LLC · Built by Grant Stubblefield · Oregon State University · 2026<br>
  <span style="color:#2a3347;">Not financial advice. Always do your own research.</span>
</div>
""", unsafe_allow_html=True)
