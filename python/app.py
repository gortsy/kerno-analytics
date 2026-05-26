# kerno/app.py
import html
import logging
import textwrap

import streamlit as st
from analyze import analyze
from data import lookup_company

logging.basicConfig(level=logging.INFO)

if "analysis_cache" not in st.session_state:
    st.session_state["analysis_cache"] = {}

st.set_page_config(
    page_title="Kerno Analytics",
    page_icon="K",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def esc(value):
    return html.escape(str(value or ""), quote=True)


def html_block(markup):
    clean_html = "\n".join(line.strip() for line in markup.splitlines())
    st.markdown(clean_html, unsafe_allow_html=True)


def trend_class(direction):
    return {"up": "up", "down": "down"}.get(str(direction).lower(), "neutral")


def metric_card(analysis, idx):
    direction = trend_class(analysis.get(f"metric{idx}_dir", ""))
    label = esc(analysis.get(f"metric{idx}_label", "Metric"))
    value = esc(analysis.get(f"metric{idx}_value", "-"))
    change = esc(analysis.get(f"metric{idx}_change", ""))
    return f"""
    <div class="metric-card metric-card--{direction}">
      <div class="metric-card__label">{label}</div>
      <div class="metric-card__value">{value}</div>
      <div class="metric-card__delta">{change}</div>
    </div>
    """


def render_result(company, analysis):
    company = {k: esc(v) for k, v in company.items()}
    analysis = {
        k: [esc(item) for item in v] if isinstance(v, list) else esc(v)
        for k, v in analysis.items()
    }

    signals = analysis.get("key_signals", [])[:6]
    tones = analysis.get("management_tone", [])[:4]
    risks = analysis.get("risks", [])[:4]
    signals_html = "".join(f"<li>{item}</li>" for item in signals)
    tones_html = "".join(f"<li>{item}</li>" for item in tones)
    risks_html = "".join(f"<li>{item}</li>" for item in risks)

    html_block(
        f"""
        <article class="ticker-card is-visible" aria-label="Analysis for {company['name']}">
          <header class="ticker-card__header">
            <div class="ticker-card__title-block">
              <h2 class="ticker-card__company">{company['name']}</h2>
              <p class="ticker-card__sector">{company['form']} filed {company['date']} · SEC EDGAR</p>
            </div>
            <div class="ticker-card__meta">
              <span class="ticker-card__ticker">{company['ticker']}</span>
              <span class="ticker-card__filing">{company['form']}</span>
            </div>
          </header>

          <section class="ticker-card__take">
            <span class="ticker-card__take-label">3-second take</span>
            <p class="ticker-card__take-text">{analysis.get('three_second_take', '')}</p>
          </section>

          <section class="ticker-card__metrics" aria-label="Key metrics">
            {metric_card(analysis, 1)}
            {metric_card(analysis, 2)}
            {metric_card(analysis, 3)}
          </section>

          <section class="ticker-card__signals">
            <h3 class="ticker-card__signals-title">Key signals</h3>
            <ul class="ticker-card__signals-list">{signals_html}</ul>
          </section>

          <div class="research-grid">
            <section class="research-panel">
              <h3>Management tone</h3>
              <ul>{tones_html}</ul>
            </section>
            <section class="research-panel">
              <h3>Risks to watch</h3>
              <ul>{risks_html}</ul>
            </section>
          </div>

          <section class="ticker-card__bottom-line">
            <span class="ticker-card__bottom-line-label">Bottom line</span>
            <p class="ticker-card__bottom-line-text">{analysis.get('bottom_line', '')}</p>
          </section>

          <p class="source-link">
            Source:
            <a href="{company['viewer_url']}" target="_blank" rel="noopener noreferrer">
              SEC EDGAR · {company['ticker']} {company['form']}
            </a>
          </p>
        </article>
        """
    )


html_block(
    """
    <style>
      :root {
        --kerno-cream: #f7f3eb;
        --kerno-cream-dark: #ede8dc;
        --kerno-grey-100: #f0eeea;
        --kerno-grey-200: #d9d6d0;
        --kerno-grey-300: #b8b4ac;
        --kerno-grey-400: #8a857c;
        --kerno-grey-500: #2e2a24;
        --kerno-orange: #e86a1a;
        --kerno-orange-dark: #c45512;
        --kerno-orange-light: #fff4eb;
        --kerno-up: #1a7a4a;
        --kerno-up-bg: #e8f5ee;
        --kerno-down: #b91c1c;
        --kerno-down-bg: #fce8e8;
        --kerno-bottom-line: #166534;
        --kerno-bottom-line-bg: #ecfdf3;
        --kerno-bottom-line-border: #86efac;
        --font-display: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
        --font-sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
        --font-mono: ui-monospace, "SF Mono", "Cascadia Code", Consolas, monospace;
      }

      .stApp {
        color: var(--kerno-grey-500);
        background:
          radial-gradient(ellipse 70% 50% at 92% 6%, rgba(232, 106, 26, 0.14), transparent 48%),
          radial-gradient(ellipse 60% 44% at 8% 86%, rgba(237, 232, 220, 0.9), transparent 55%),
          var(--kerno-cream);
        font-family: var(--font-sans);
      }

      #MainMenu, footer, header { visibility: hidden; }
      .block-container {
        max-width: 80rem;
        padding: 1.25rem 2rem 3rem;
      }

      h1, h2, h3, .brand-name {
        font-family: var(--font-display);
        letter-spacing: 0;
      }

      .brand-bar {
        position: sticky;
        top: 0;
        z-index: 20;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        margin: -1.25rem -2rem 0;
        padding: 1rem 2rem;
        background: rgba(247, 243, 235, 0.86);
        border-bottom: 1px solid rgba(217, 214, 208, 0.9);
        backdrop-filter: blur(12px);
      }

      .brand-lockup {
        display: inline-flex;
        align-items: center;
        gap: 0.75rem;
      }

      .brand-mark {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2.25rem;
        height: 2.25rem;
        color: #fff;
        font-weight: 800;
        border-radius: 8px;
        background: linear-gradient(135deg, var(--kerno-orange), var(--kerno-orange-dark));
        box-shadow: 0 8px 32px rgba(232, 106, 26, 0.18);
      }

      .brand-name {
        margin: 0;
        font-size: 1.35rem;
        font-weight: 600;
      }

      .brand-nav {
        display: flex;
        align-items: center;
        gap: 1rem;
        color: var(--kerno-grey-400);
        font-size: 0.9rem;
      }

      .hero-band {
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(19rem, 0.82fr);
        align-items: center;
        gap: clamp(1.5rem, 4vw, 3rem);
        margin: 0 -2rem 2rem;
        padding: 2rem 2rem 1.5rem;
        margin-bottom: 1rem;
        background: linear-gradient(165deg, var(--kerno-cream) 0%, var(--kerno-cream-dark) 52%, var(--kerno-grey-100) 100%);
        border-bottom: 1px solid var(--kerno-grey-200);
      }

      .eyebrow {
        display: inline-block;
        margin-bottom: 0.75rem;
        padding: 0.3rem 0.6rem;
        color: var(--kerno-orange);
        background: var(--kerno-orange-light);
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }

      .hero-title {
        max-width: 42rem;
        margin: 0 0 1rem;
        color: var(--kerno-grey-500);
        font-size: clamp(2.35rem, 5.5vw, 4.1rem);
        line-height: 1.05;
        font-weight: 600;
      }

      .hero-copy {
        max-width: 42rem;
        margin: 0;
        color: var(--kerno-grey-400);
        font-size: 1.12rem;
        line-height: 1.7;
      }

      .hero-proof {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.75rem;
      }

      .proof-stat {
        padding: 1rem;
        background: rgba(255, 255, 255, 0.62);
        border: 1px solid var(--kerno-grey-200);
        border-radius: 8px;
      }

      .proof-stat strong {
        display: block;
        color: var(--kerno-orange);
        font-family: var(--font-mono);
        font-size: 1.35rem;
      }

      .proof-stat span {
        color: var(--kerno-grey-400);
        font-size: 0.8rem;
      }

      .workspace-shell {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 18rem;
        gap: 1.5rem;
        align-items: start;
      }

      .control-panel,
      .side-panel,
      .empty-state,
      .research-panel {
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid var(--kerno-grey-200);
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(92, 88, 80, 0.08);
      }

      .control-panel { padding: 1rem; margin-bottom: 1.25rem; }
      .side-panel { padding: 1.25rem; }

      .panel-label {
        margin: 0 0 0.75rem;
        color: var(--kerno-grey-400);
        font-family: var(--font-mono);
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      .stTextInput > div > div > input {
        color: var(--kerno-grey-500) !important;
        background: #fff !important;
        border: 1px solid var(--kerno-grey-200) !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        font-family: var(--font-mono) !important;
        letter-spacing: 0.06em !important;
        padding: 0.75rem 0.9rem !important;
      }

      .stTextInput > div > div > input:focus {
        border-color: var(--kerno-orange) !important;
        box-shadow: 0 0 0 2px rgba(232, 106, 26, 0.12) !important;
      }

      .stButton > button {
        min-height: 2.75rem;
        color: #fff !important;
        background: linear-gradient(135deg, var(--kerno-orange), var(--kerno-orange-dark)) !important;
        border: 0 !important;
        border-radius: 999px !important;
        box-shadow: 0 8px 32px rgba(232, 106, 26, 0.18) !important;
        font-weight: 700 !important;
      }

      div[data-testid="stHorizontalBlock"] .stButton > button {
        color: var(--kerno-grey-500) !important;
        background: #fff !important;
        border: 1px solid var(--kerno-grey-200) !important;
        box-shadow: none !important;
      }

      .ticker-card {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        padding: clamp(1.25rem, 3vw, 2rem);
        background: #fff;
        border: 1px solid var(--kerno-grey-200);
        border-radius: 12px;
        box-shadow: 0 20px 50px -12px rgba(60, 55, 48, 0.15);
        overflow: visible;
      }

      .ticker-card__header {
        display: flex;
        visibility: visible !important;
        opacity: 1 !important;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        padding-bottom: 1.25rem;
        border-bottom: 1px solid var(--kerno-grey-200);
      }

      .ticker-card__company {
        margin: 0 0 0.3rem;
        color: var(--kerno-grey-500);
        font-size: clamp(1.5rem, 3vw, 1.9rem);
      }

      .ticker-card__sector,
      .source-link {
        margin: 0;
        color: var(--kerno-grey-400);
        font-size: 0.86rem;
      }

      .ticker-card__meta {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 0.4rem;
      }

      .ticker-card__ticker {
        color: var(--kerno-grey-400);
        font-family: var(--font-mono);
        font-weight: 700;
      }

      .ticker-card__filing {
        padding: 0.25rem 0.5rem;
        color: var(--kerno-orange);
        background: var(--kerno-orange-light);
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
      }

      .ticker-card__take {
        padding: 1.25rem;
        background: var(--kerno-cream);
        border-left: 4px solid var(--kerno-orange);
        border-radius: 0 8px 8px 0;
      }

      .ticker-card__take-label,
      .ticker-card__bottom-line-label {
        display: block;
        margin-bottom: 0.35rem;
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      .ticker-card__take-label { color: var(--kerno-orange); }

      .ticker-card__take-text {
        margin: 0;
        color: var(--kerno-grey-500);
        font-size: 1.08rem;
        font-weight: 600;
        line-height: 1.55;
      }

      .ticker-card__metrics,
      .research-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1rem;
      }

      .research-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .metric-card {
        padding: 1rem;
        border: 1px solid var(--kerno-grey-200);
        border-radius: 8px;
      }

      .metric-card--up { background: var(--kerno-up-bg); border-color: #a7d4bc; }
      .metric-card--down { background: var(--kerno-down-bg); border-color: #f5b8b8; }
      .metric-card--neutral { background: #fff; }

      .metric-card__label,
      .ticker-card__signals-title,
      .research-panel h3 {
        margin: 0 0 0.55rem;
        color: var(--kerno-grey-400);
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }

      .metric-card__value {
        color: var(--kerno-grey-500);
        font-size: 1.45rem;
        font-weight: 800;
        line-height: 1.2;
      }

      .metric-card--up .metric-card__value,
      .metric-card--up .metric-card__delta { color: var(--kerno-up); }
      .metric-card--down .metric-card__value,
      .metric-card--down .metric-card__delta { color: var(--kerno-down); }

      .metric-card__delta {
        color: var(--kerno-grey-400);
        font-size: 0.82rem;
        font-weight: 700;
      }

      .ticker-card__signals {
        padding: 1.25rem;
        background: var(--kerno-grey-100);
        border-radius: 8px;
      }

      .ticker-card__signals-list,
      .research-panel ul {
        margin: 0;
        padding-left: 1.2rem;
        color: var(--kerno-grey-500);
      }

      .ticker-card__signals-list li,
      .research-panel li {
        margin-bottom: 0.45rem;
        line-height: 1.55;
      }

      .ticker-card__signals-list li::marker,
      .research-panel li::marker {
        color: var(--kerno-orange);
      }

      .research-panel { padding: 1rem; box-shadow: none; }

      .ticker-card__bottom-line {
        padding: 1.25rem;
        color: var(--kerno-bottom-line);
        background: var(--kerno-bottom-line-bg);
        border: 1px solid var(--kerno-bottom-line-border);
        border-radius: 8px;
      }

      .ticker-card__bottom-line-label { color: var(--kerno-bottom-line); }
      .ticker-card__bottom-line-text {
        margin: 0;
        color: var(--kerno-bottom-line);
        font-weight: 600;
        line-height: 1.55;
      }

      .source-link a {
        color: var(--kerno-orange);
        text-decoration: none;
      }

      .empty-state {
        padding: 2rem;
        color: var(--kerno-grey-400);
        text-align: center;
      }

      .error-box {
        padding: 1rem;
        color: var(--kerno-down);
        background: var(--kerno-down-bg);
        border: 1px solid #f5b8b8;
        border-radius: 8px;
      }

      .footer-note {
        margin-top: 2rem;
        color: var(--kerno-grey-400);
        font-size: 0.82rem;
        text-align: center;
      }

      @media (max-width: 58rem) {
        .hero-band,
        .workspace-shell {
          grid-template-columns: 1fr;
        }
        .ticker-card__metrics,
        .research-grid,
        .hero-proof {
          grid-template-columns: 1fr;
        }
      }

      @media (max-width: 40rem) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .brand-bar, .hero-band { margin-left: -1rem; margin-right: -1rem; padding-left: 1rem; padding-right: 1rem; }
        .brand-nav { display: none; }
        .ticker-card__header { flex-direction: column; }
        .ticker-card__meta { align-items: flex-start; }
      }
    </style>
    """
)

html_block(
    """
    <div class="brand-bar">
      <div class="brand-lockup">
        <span class="brand-mark">K</span>
        <p class="brand-name">Kerno Analytics</p>
      </div>
      <nav class="brand-nav" aria-label="Product">
        <span>Live analysis</span>
        <span>SEC EDGAR</span>
        <span>Not financial advice</span>
      </nav>
    </div>

    <section class="hero-band" aria-label="Introduction">
      <div>
        <span class="eyebrow">SEC filing intelligence</span>
        <h1 class="hero-title">The filing desk built for institutional research</h1>
        <p class="hero-copy">
          Kerno transforms 10-K and 10-Q disclosures into structured verdicts:
          metrics, signals, and a bottom-line read you can act on before the market does.
        </p>
      </div>
      <div class="hero-proof" aria-label="Platform metrics">
        <div class="proof-stat"><strong>10-K</strong><span>Annual filings parsed</span></div>
        <div class="proof-stat"><strong>10-Q</strong><span>Quarterly updates summarized</span></div>
        <div class="proof-stat"><strong>&lt;3s</strong><span>Top-line research take</span></div>
        <div class="proof-stat"><strong>SEC</strong><span>EDGAR-sourced workflow</span></div>
      </div>
    </section>
    """
)

left, right = st.columns([3.2, 1], gap="large")

with left:
    html_block('<section class="control-panel"><p class="panel-label">Analyze a filing</p>')
    col1, col2 = st.columns([4, 1])
    with col1:
        typed = st.text_input(
            label="Ticker",
            placeholder="Enter any US ticker: AAPL, NVDA, BRK.B",
            label_visibility="collapsed",
            key="ticker_input",
            max_chars=10,
        )
    with col2:
        analyze_clicked = st.button("Analyze", use_container_width=True)

    html_block('<p class="panel-label" style="margin-top:.75rem;">Quick picks</p>')
    quick_tickers = ["AAPL", "NVDA", "MSFT", "TSLA", "AMZN", "META"]
    quick_cols = st.columns(len(quick_tickers))
    for i, qt in enumerate(quick_tickers):
        with quick_cols[i]:
            if st.button(qt, key=f"quick_{qt}", use_container_width=True):
                st.session_state["pending_ticker"] = qt
    html_block("</section>")

    run_ticker = None
    if analyze_clicked and typed:
        run_ticker = typed.strip().upper()
    elif "pending_ticker" in st.session_state:
        run_ticker = st.session_state.pop("pending_ticker")

    if run_ticker:
        with st.spinner(f"Pulling {run_ticker} from SEC EDGAR..."):
            company = lookup_company(run_ticker)

        if "error" in company:
            html_block(
                f"""
                <div class="error-box">
                  <strong>Could not analyze {esc(run_ticker)}</strong><br>
                  {esc(company['error'])}
                </div>
                """
            )
            st.stop()

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
                    html_block(
                        f"""
                        <div class="error-box">
                          <strong>AI analysis failed</strong><br>
                          {esc(e)}
                        </div>
                        """
                    )

        if result:
            if result.get("sourced_from_filing"):
                st.success("Figures sourced directly from SEC filing")
            else:
                st.warning("Filing text unavailable - figures from AI training knowledge")
            render_result(company, result)
    else:
        html_block(
            """
            <div class="empty-state">
              <span class="eyebrow">Ready</span>
              <h2>Enter a ticker to generate a live filing card</h2>
              <p>
                Kerno will find the latest 10-K or 10-Q, extract the relevant text,
                and return a structured research summary.
              </p>
            </div>
            """
        )

with right:
    html_block(
        """
        <aside class="side-panel">
          <p class="panel-label">Workflow</p>
          <ol style="margin:0; padding-left:1.25rem; color:var(--kerno-grey-500); line-height:1.7;">
            <li>Enter a listed US ticker.</li>
            <li>Kerno finds the latest SEC filing.</li>
            <li>Gemini returns metrics, signals, tone, and risks.</li>
          </ol>
        </aside>
        <br>
        <aside class="side-panel">
          <p class="panel-label">Security posture</p>
          <p style="margin:0; color:var(--kerno-grey-400); line-height:1.65;">
            API keys stay in Streamlit secrets or local environment variables.
            They are never rendered into the browser.
          </p>
        </aside>
        """
    )

with st.sidebar:
    st.markdown("### Kerno Analytics")
    st.markdown(
        """
        Institutional-style SEC filing summaries for faster first-pass research.

        Data: SEC EDGAR  
        AI: Google Gemini  
        Not financial advice.
        """
    )

html_block(
    """
    <div class="footer-note">
      Kerno Analytics LLC · Built by Grant Stubblefield · Always do your own research.
    </div>
    """,
)
