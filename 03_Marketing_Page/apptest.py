import math
import streamlit as st
import sqlite3
import pandas as pd
import requests
import os
import yfinance as yf
import textwrap
from datetime import datetime, timedelta

# ==========================================================
# 🔢 INTENSITY NORMALIZATION ENGINE
# ==========================================================
def normalize_intensity(raw_score: float) -> tuple:
    """
    Converts a raw intensity score into:
    - a 0–100 normalized score
    - a category label
    - a rounded display value
    - an arrow indicator
    """
    if raw_score is None or raw_score <= 0:
        return 0, "Low", 0, "→"

    normalized = min(100, math.log10(max(raw_score, 1)) * 20)
    display_value = round(normalized)

    if display_value < 20:
        label = "Low"; arrow = "↓"
    elif display_value < 40:
        label = "Moderate"; arrow = "→"
    elif display_value < 60:
        label = "High"; arrow = "↑"
    elif display_value < 80:
        label = "Very High"; arrow = "↑"
    else:
        label = "Extreme"; arrow = "↑↑"

    return display_value, label, display_value, arrow


# ==========================================================
# 🧱 STREAMLIT PAGE CONFIG
# ==========================================================
st.set_page_config(
    page_title="Smart Money Radar — Live Insider Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================================
# 🗺️ PATH RESOLUTION FOR DATA STORAGE
# ==========================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "02_Database", "insider_vault.db")

try:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn_init = sqlite3.connect(DB_PATH)
    cursor_init = conn_init.cursor()
    cursor_init.execute("""
    CREATE TABLE IF NOT EXISTS beta_subscribers (
        email TEXT PRIMARY KEY,
        signup_date TEXT
    )
    """)
    conn_init.commit()
    conn_init.close()
except Exception as e:
    st.error(f"Database Initialization Warning: {e}")

# ==========================================================
# 🎨 CSS + DESIGN
# ==========================================================
st.markdown(textwrap.dedent("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');
    html { scroll-behavior: smooth; }
    html, body, [data-testid="stAppViewContainer"], .main { 
        background-color: #f8fafc !important;
        color: #1e293b !important;
        font-family: 'Inter', sans-serif !important;
    }
    div.block-container { padding: 4.5rem max(4vw, 20px) !important; max-width: 1400px; }
    [data-testid="stHeader"], footer { visibility: hidden !important; }
    h1,h2,h3,h4,h5,h6 { color: #0f172a !important; letter-spacing: -0.02em; }
    label, p, span { color: #334155 !important; }
    [data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: #2962ff;
        z-index: 999999;
    }
    .premium-navbar { position: fixed; top: 3px; left: 0; width: 100%; height: 60px; background: #0f172a; border-bottom: 1px solid rgba(255,255,255,0.1); display:flex; justify-content:space-between; align-items:center; padding:0 max(4vw,20px); z-index:99999; }
    .nav-logo { font-family: 'JetBrains Mono', monospace; font-weight:700; font-size:1rem; color:#fff; display:flex; align-items:center; gap:8px; }
    .nav-cta-btn { background:#2962ff; color:#fff !important; padding:8px 16px; border-radius:4px; font-size:0.85rem; font-weight:600; text-decoration:none !important; transition:background 0.2s ease; }
    .nav-cta-btn:hover { background:#1e4bd8; }
    .ticker-wrap { width:100%; overflow:hidden; background-color:#020617; padding:12px 0; margin-top:-20px; margin-bottom:30px; border-radius:4px; border:1px solid #1e293b; }
    .ticker { display:inline-block; white-space:nowrap; padding-left:100%; animation:marquee 30s linear infinite; }
    .ticker-item { display:inline-block; padding:0 2.5rem; font-family:'JetBrains Mono', monospace; font-size:14px; font-weight:700; color:#38bdf8; }
    .ticker-item span.up { color:#22c55e !important; font-weight:700; }
    .ticker-item span.down { color:#f87171 !important; font-weight:700; }
    @keyframes marquee { 0% { transform: translate3d(0,0,0); } 100% { transform: translate3d(-100%,0,0); } }
    .hero-panel { text-align:center; padding:30px 24px; background:linear-gradient(135deg,#0f172a,#1e293b); border-radius:8px; margin-bottom:2.5rem; box-shadow:0 4px 6px -1px rgba(0,0,0,0.1); }
    .brand-badge { display:inline-flex; align-items:center; gap:6px; background:rgba(41,98,255,0.15); color:#60a5fa; padding:6px 14px; border-radius:100px; font-size:0.75rem; font-weight:700; margin-bottom:16px; border:1px solid rgba(41,98,255,0.3); letter-spacing:0.04em; }
    .hero-main-title { font-size:2.5rem; font-weight:800; color:#fff !important; line-height:1.2; margin-bottom:16px; letter-spacing:-0.02em; }
    .hero-desc { font-size:1.05rem; color:#94a3b8 !important; line-height:1.6; max-width:840px; margin:0 auto; }
    .trust-banner { display:flex; justify-content:center; align-items:center; gap:max(5vw,24px); background:#fff; border:1px solid #e2e8f0; border-radius:8px; padding:22px; margin-bottom:2.5rem; box-shadow:0 1px 3px rgba(0,0,0,0.02); }
    .trust-item { text-align:center; } .trust-val { font-size:1.5rem; font-weight:700; color:#0f172a !important; font-family:'JetBrains Mono', monospace; } .trust-lbl { font-size:0.7rem; color:#64748b !important; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-top:4px; }
    .trust-divider { width:1px; height:30px; background:#e2e8f0; }
    .signal-card { background:#fff; padding:24px; border-radius:8px; border:1px solid #e2e8f0; margin-bottom:18px; box-shadow:0 1px 3px rgba(0,0,0,0.02); }
    .pill-green { background-color: rgba(34,197,94,0.1); color:#166534 !important; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; border:1px solid rgba(34,197,94,0.15); }
    .pill-blue { background-color: rgba(41,98,255,0.1); color:#1e40af !important; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; border:1px solid rgba(41,98,255,0.15); }
    .pill-orange { background-color: rgba(249,115,22,0.1); color:#c2410c !important; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; border:1px solid rgba(249,115,22,0.15); }
    .pill-purple { background-color: rgba(147,51,234,0.1); color:#6b21a8 !important; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; border:1px solid rgba(147,51,234,0.15); }
    .live-pill-discount { background: rgba(249,115,22,0.1); color:#c2410c !important; padding:6px 12px; border-radius:4px; font-weight:600; font-size:0.8rem; border:1px dashed rgba(249,115,22,0.3); flex: 1; text-align: center; }
    .live-pill-standard { background:#f1f5f9; color:#475569 !important; padding:6px 12px; border-radius:4px; font-weight:600; font-size:0.8rem; border:1px solid #e2e8f0; flex: 1; text-align: center; }
    .phone-housing { position:sticky; top:80px; background:#fff; border-radius:36px; padding:12px; border:2px solid #cbd5e1; max-width:360px; margin:0 auto 2rem auto; box-shadow:0 20px 25px -5px rgba(0,0,0,0.05); }
    .phone-screen { background:#0f172a; border-radius:26px; overflow:hidden; border:1px solid #1e293b; min-height:520px; display:flex; flex-direction:column; justify-content:space-between; }
    .phone-header { background:#1e293b; padding:20px 14px 14px 14px; color:#fff; text-align:center; border-bottom:1px solid #334155; }
    .phone-app-title { font-size:1.05rem; font-weight:700; letter-spacing:-0.01em; color:#fff !important; }
    .phone-app-sub { color:#94a3b8 !important; font-size:0.68rem; font-weight:500; margin-top:4px; display:flex; align-items:center; justify-content:center; }
    .phone-body { padding:12px; flex-grow:1; display:flex; flex-direction:column; gap:8px; }
    .phone-metric-strip { background:#1e293b; border-radius:6px; padding:10px; border:1px solid #334155; display:flex; justify-content:space-between; margin-bottom:4px; }
    .phone-m-card { text-align:center; flex:1; } .phone-m-val { font-size:0.95rem; font-weight:700; color:#4ade80 !important; font-family:'JetBrains Mono', monospace; } .phone-m-lbl { font-size:0.6rem; color:#cbd5e1 !important; font-weight:700; text-transform:uppercase; }
    .phone-alert-card { background:#1e293b; border-radius:6px; padding:12px; border:1px solid #334155; }
    .phone-alert-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; }
    .phone-ticker { font-size:0.95rem; font-weight:700; color:#fff !important; font-family:'JetBrains Mono', monospace; }
    .phone-badge-premium { background:rgba(41,98,255,0.15); color:#60a5fa !important; font-size:0.6rem; font-weight:700; padding:2px 5px; border-radius:3px; border:1px solid rgba(41,98,255,0.2); }
    .phone-insider { font-size:0.82rem; color:#fff !important; font-weight:700 !important; }
    .phone-price-row span { color:#e2e8f0 !important; font-weight:600 !important; font-size:0.78rem !important; }
    .phone-glow-dot { width:5px; height:5px; background-color:#22c55e; border-radius:50px; display:inline-block; margin-right:5px; }
    .config-card { background:#fff; border:1px solid #e2e8f0; border-radius:8px; padding:24px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.02); }
    .config-header { font-size:1.05rem; font-weight:700; color:#0f172a !important; margin-bottom:12px; }
    .bullet-item { font-size:0.88rem; color:#334155 !important; margin-bottom:8px; display:flex; align-items:center; gap:8px; }
    .bullet-dot { width:5px; height:5px; background:#2962ff; border-radius:50%; }
    div[data-testid="stTextInput"] input { background-color:#fff !important; color:#0f172a !important; border:1px solid #cbd5e1 !important; border-radius:4px !important; padding:12px !important; }
    div[data-testid="stTextInput"] input:focus { border-color:#2962ff !important; box-shadow:0 0 0 1px #2962ff !important; }
    div[data-testid="stFormSubmitButton"] button, div.stButton button, div[data-testid="stFormSubmitButton"] button p, div.stButton button p { background-color:#2962ff !important; color:#fff !important; font-size:0.98rem !important; font-weight:700 !important; letter-spacing:0.02em !important; }
    div[data-testid="stFormSubmitButton"] button:hover, div.stButton button:hover { background-color:#1e4bd8 !important; }
    .review-box { background:#fff; border:1px solid #e2e8f0; border-radius:8px; padding:16px; margin-top:16px; box-shadow:0 1px 3px rgba(0,0,0,0.02); }
    .star-row { color:#f59e0b; font-size:0.9rem; margin-bottom:4px; }
    .sec-archive-timestamp { margin-top:14px; color:#475569 !important; font-size:0.8rem; font-family:'JetBrains Mono', monospace; font-weight:600; }
    .legal-disclaimer-footer { margin-top:4rem; padding-top:24px; border-top:1px solid #e2e8f0; font-size:0.78rem; color:#475569 !important; line-height:1.6; text-align:justify; }
    </style>
"""), unsafe_allow_html=True)

# ==========================================================
# 🗺️ FLOATING NAVBAR
# ==========================================================
st.markdown(textwrap.dedent("""
    <div class="premium-navbar">
        <div class="nav-logo">⚡ SMART MONEY RADAR</div>
        <a class="nav-cta-btn" href="#join-terminal-anchor">Access Terminal</a>
    </div>
"""), unsafe_allow_html=True)

# ==========================================================
# 📡 TICKER STREAM
# ==========================================================
st.markdown(textwrap.dedent("""
<div class="ticker-wrap">
    <div class="ticker">
        <div class="ticker-item">🍏 AAPL <span class="up">▲ $180.50 (+1.2%)</span></div>
        <div class="ticker-item">🤖 MSFT <span class="down">▼ $420.20 (-0.4%)</span></div>
        <div class="ticker-item">🚗 TSLA <span class="up">▲ $175.00 (+2.8%)</span></div>
        <div class="ticker-item">📦 AMZN <span class="up">▲ $185.30 (+0.9%)</span></div>
        <div class="ticker-item">🔍 GOOGL <span class="down">▼ $172.10 (-1.1%)</span></div>
        <div class="ticker-item">🌐 NVDA <span class="up">▲ $900.40 (+4.3%)</span></div>
    </div>
</div>
"""), unsafe_allow_html=True)

# ==========================================================
# 🏛️ HERO PANEL
# ==========================================================
st.markdown(textwrap.dedent("""
    <div class="hero-panel">
        <div class="brand-badge">⚡ SMART MONEY RADAR TERMINAL</div>
        <div class="hero-main-title">Commission-free insider tracking for everyone.</div>
        <div class="hero-desc">
            When public company CEOs, CFOs, and board members deploy substantial sums of their own personal family capital into their own stock, they aren't speculating—they are acting on non-public execution visibility. Our automation engine monitors raw SEC Form 4 wires 24/7 and ranks them based on relative intensity to isolate real conviction alerts.
        </div>
    </div>
"""), unsafe_allow_html=True)

# ==========================================================
# 📊 DATA LOADING
# ==========================================================
try:
    conn = sqlite3.connect(DB_PATH)
    total_tracked_df = pd.read_sql_query(
        "SELECT COUNT(*) as total_count, SUM(total_value) as total_val FROM insider_trades",
        conn
    )
    total_count = int(total_tracked_df['total_count'].iloc[0] or 0)
    total_val = float(total_tracked_df['total_val'].iloc[0] or 0)

    query = """
        SELECT ticker as [Ticker], company as [Company], insider_name as [Insider], 
               position as [Position], price as [Buy Price], total_value as [Total Value], 
               market_cap as [Market Cap], avg_volume as [Avg Volume], 
               intensity_score as [Intensity Score], trigger_type as [Trigger Type], filing_date as [Filing Date]
        FROM insider_trades 
        ORDER BY [Intensity Score] DESC, filing_date DESC 
        LIMIT 5
    """
    df_signals = pd.read_sql_query(query, conn)
    conn.close()
except Exception:
    df_signals = pd.DataFrame()
    total_count, total_val = 0, 0

formatted_total_capital = f"${total_val:,.2f}" if total_val > 0 else "$0.00"
formatted_total_filings = f"{total_count:,} Filings" if total_count > 0 else "0 Filings"

st.markdown(textwrap.dedent(f"""
    <div class="trust-banner">
        <div class="trust-item">
            <div class="trust-val">{formatted_total_capital}</div>
            <div class="trust-lbl">In Deployed Capital Tracked</div>
        </div>
        <div class="trust-divider"></div>
        <div class="trust-item">
            <div class="trust-val">{formatted_total_filings}</div>
            <div class="trust-lbl">Raw SEC Wires Ingested</div>
        </div>
        <div class="trust-divider"></div>
        <div class="trust-item">
            <div class="trust-val">Trustscore 4.7</div>
            <div class="trust-lbl">★★★★★ Beta Feed Rating</div>
        </div>
    </div>
"""), unsafe_allow_html=True)

# ==========================================================
# 📡 DUAL COLUMN LAYOUT
# ==========================================================
col_left, col_right = st.columns([11, 9], gap="large")

# ---------------- LEFT COLUMN: LIVE STREAM ----------------
with col_left:
    st.markdown(
        '<h3 style="font-weight:700; font-size:1.25rem; margin-top:0; margin-bottom:4px;">📡 Public Terminal Live Stream (Top Relative Impact Moves)</h3>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<p style="color:#475569 !important; font-size:0.9rem; margin-bottom:20px;">Real-time execution views prioritized by company scale intensity and multi-executive clustering maps:</p>',
        unsafe_allow_html=True
    )

    if not df_signals.empty:
        for idx, row in df_signals.iterrows():
            formatted_cash = f"${row['Total Value']:,.2f}"
            insider_buy_price = row.get('Buy Price', None)
            ticker_symbol = row.get('Ticker', "N/A")
            pos_label = str(row.get('Position', "")).upper()
            trigger_tag = str(row.get('Trigger Type', ""))
            intensity = row.get('Intensity Score', None)
            mcap_display = row.get('Market Cap', "N/A")
            vol_val = row.get('Avg Volume', None)
            vol_display = f"{int(vol_val):,}" if pd.notna(vol_val) and vol_val else "Data Unavailable"

            norm_score, norm_label, display_score, arrow = normalize_intensity(intensity)

            trigger_upper = trigger_tag.upper() if isinstance(trigger_tag, str) else ""
            if "CLUSTER" in trigger_upper and "WHALE" in trigger_upper:
                badge_style = '<span class="pill-purple">🔥 CLUSTER + WHALE ALIGNMENT</span>'
            elif "CLUSTER" in trigger_upper:
                badge_style = '<span class="pill-blue">🏛️ MULTI-INSIDER CLUSTER</span>'
            elif "WHALE" in trigger_upper:
                badge_style = '<span class="pill-orange">🐋 HIGH-INTENSITY WHALE</span>'
            else:
                badge_style = '<span class="pill-green">⚡ STANDARD ACTIVE PURCHASING</span>'

            # --- DUAL TIME-FRAME WORKFLOW ENGINE (YFINANCE) ---
            wire_perf_html = '<div class="live-pill-standard">Filing price status unavailable</div>'
            trade_perf_html = '<div class="live-pill-standard">Insider entry delta unavailable</div>'
            
            try:
                filing_date_raw = row.get('Filing Date', None)
                stock_engine = yf.Ticker(ticker_symbol)
                
                if filing_date_raw:
                    filing_date = pd.to_datetime(filing_date_raw).date()
                    start_date = filing_date - timedelta(days=5)
                    end_date = datetime.today().date() + timedelta(days=1)
                    history_slice = stock_engine.history(start=start_date, end=end_date)
                else:
                    history_slice = stock_engine.history(period="1mo")

                if not history_slice.empty:
                    history_slice = history_slice.sort_index()
                    current_market_price = float(history_slice['Close'].iloc[-1])
                    
                    # A. Calculation since Wire Alert (Filing Date)
                    entry_wire_price = None
                    if filing_date_raw:
                        try:
                            wire_rows = history_slice.loc[history_slice.index.date >= filing_date]
                            if not wire_rows.empty:
                                entry_wire_price = float(wire_rows['Close'].iloc[0])
                        except Exception:
                            entry_wire_price = None
                    
                    if entry_wire_price is None:
                        entry_wire_price = float(history_slice['Close'].iloc[0])
                        
                    wire_perf_pct = ((current_market_price - entry_wire_price) / entry_wire_price) * 100
                    if wire_perf_pct >= 0:
                        wire_perf_html = f'<div class="live-pill-standard" style="color:#166534 !important; background:rgba(34, 197, 94, 0.06); border-color:rgba(34, 197, 94, 0.15);">📈 Wire Alert: +{wire_perf_pct:.1f}%</div>'
                    else:
                        wire_perf_html = f'<div class="live-pill-discount">📉 Wire Alert: {wire_perf_pct:.1f}%</div>'

                    # B. Calculation since True Trade Execution Date (vs. Insider Cost Basis)
                    if insider_buy_price and insider_buy_price > 0:
                        trade_perf_pct = ((current_market_price - float(insider_buy_price)) / float(insider_buy_price)) * 100
                        if trade_perf_pct >= 0:
                            trade_perf_html = f'<div class="live-pill-standard" style="color:#166534 !important; background:rgba(34, 197, 94, 0.06); border-color:rgba(34, 197, 94, 0.15);">🏷️ Market Premium: +{trade_perf_pct:.1f}%</div>'
                        else:
                            # Negative indicates stock dropped below insider buy price -> buying at a discount!
                            trade_perf_html = f'<div class="live-pill-discount" style="background: rgba(34, 197, 94, 0.1); color: #166534 !important; border-color: rgba(34, 197, 94, 0.3);">🎁 Market Discount: {abs(trade_perf_pct):.1f}%</div>'
            except Exception:
                pass

            card_html = (
f'<div class="signal-card">'
f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">'
f'<div><span style="font-weight: 700; font-size: 1.2rem; font-family:\'JetBrains Mono\', monospace; margin-right: 8px; color: #0f172a;">{ticker_symbol}</span>{badge_style}</div>'
f'<span style="color: #166534; font-weight: 700; font-size: 1.20rem; font-family: \'JetBrains Mono\', monospace;">+{formatted_cash}</span>'
f'</div>'
f'<div style="margin-top:10px; margin-bottom:14px;">'
f'<div style="font-size:0.85rem; font-weight:700; color:#334155; margin-bottom:4px;">Impact Level: {norm_label} ({display_score}/100) {arrow}</div>'
f'<div style="width:100%; background:#e2e8f0; height:10px; border-radius:6px;">'
f'<div style="width:{display_score}%; height:10px; border-radius:6px; background:linear-gradient(90deg, #60a5fa, #2563eb);"></div>'
f'</div>'
f'</div>'
f'<div style="color: #334155; font-size: 0.9rem; line-height: 1.4; margin-bottom: 12px;">'
f'<strong style="color: #64748b;">Company:</strong> {row.get("Company", "N/A")} (Size: {mcap_display} | Avg Vol: {vol_display})<br>'
f'<strong style="color: #64748b;">Purchaser:</strong> {row.get("Insider", "N/A")} (<span style="color:#475569;">{pos_label}</span>)'
f'</div>'
f'<div style="margin-bottom: 12px; display: flex; gap: 10px; width: 100%;">{wire_perf_html}{trade_perf_html}</div>'
f'<div style="background: #f1f5f9; padding: 10px 14px; border-radius: 4px; font-size: 0.85rem; color: #334155; border-left: 3px solid #2962ff; line-height:1.4;">'
f'💡 <strong>Relative Impact Matrix:</strong> Deployed sum carries unique structural value based on core company liquidity profiles. Out-of-pocket setup confirms deep insider conviction.'
f'</div>'
f'<div class="sec-archive-timestamp">SEC Archive Timestamp: {row.get("Filing Date", "N/A")}</div>'
f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info("Terminal database buffer loading. Awaiting live pipeline data updates...")

# ---------------- RIGHT COLUMN: PHONE MOCKUP (STATIC) + SUBSCRIPTION ----------------
with col_right:
    p_ticker = "NVDA"
    p_insider = "Jensen Huang"
    p_pos = "CHIEF EXECUTIVE OFFICER"
    p_val = "+$12,450,000"
    p_tag = "🐋 HIGH-INTENSITY WHALE"

    phone_html = textwrap.dedent(f"""
        <div class="phone-housing">
            <div class="phone-screen">
                <div class="phone-header">
                    <div class="phone-app-title">⚡ Smart Money Radar</div>
                    <div class="phone-app-sub"><span class="phone-glow-dot"></span>Active Premium Live Feed Connection</div>
                </div>
                <div class="phone-body">
                    <div class="phone-metric-strip">
                        <div class="phone-m-card" style="border-right: 1px solid #334155;">
                            <div class="phone-m-val">2.9s</div>
                            <div class="phone-m-lbl">Wire Latency</div>
                        </div>
                        <div class="phone-m-card">
                            <div class="phone-m-val">99.8%</div>
                            <div class="phone-m-lbl">Match Precision</div>
                        </div>
                    </div>
                    <div class="phone-alert-card" style="border-left: 3px solid #2962ff;">
                        <div class="phone-alert-top">
                            <span class="phone-ticker">{p_ticker}</span>
                            <span class="phone-badge-premium">{p_tag}</span>
                        </div>
                        <div class="phone-insider">{p_insider}</div>
                        <div class="phone-price-row">
                            <span style="font-size:0.7rem; color:#94a3b8 !important;">{p_pos}</span>
                            <span style="color:#4ade80 !important; font-weight:700;">{p_val}</span>
                        </div>
                    </div>
                    <p style="color:#64748b; font-size:0.65rem; text-align:center; margin-top:8px; margin-bottom:4px; font-weight:600; text-transform:uppercase;">Mockup Platform Stream Context</p>
                    <div class="phone-alert-card" style="border-left: 3px solid #e2e8f0; opacity:0.4;">
                        <div class="phone-alert-top">
                            <span class="phone-ticker">AMZN</span>
                            <span style="color:#94a3b8; font-size:0.6rem; font-weight:600;">Historical</span>
                        </div>
                        <div class="phone-insider">Director Buy Layer</div>
                    </div>
                </div>
            </div>
        </div>
    """).strip()

    st.markdown(phone_html, unsafe_allow_html=True)

    # ==========================================================
    # 📝 SUBSCRIPTION FORM 
    # ==========================================================
    st.markdown(textwrap.dedent("""
        <div id="join-terminal-anchor" class="config-card" style="margin-top: 12px;">
            <div class="config-header">🔒 Live Configuration Access Control</div>
            <p style="color: #334155 !important; font-size: 0.88rem; line-height: 1.5; margin-bottom: 14px;">
                Public web streams are heavily rate-limited. Configure your active terminal profile setup below to activate custom settings:
            </p>
            <div class="bullet-item"><div class="bullet-dot"></div><span><strong>Unrestricted Rolling Buffer:</strong> Unlocks past data histories</span></div>
            <div class="bullet-item"><div class="bullet-dot"></div><span><strong>Instant Execution Webhooks:</strong> Immediate mobile telemetry push</span></div>
            <div class="bullet-item"><div class="bullet-dot"></div><span><strong>Cluster Signals:</strong> Triggers when multiple executives buy simultaneously</span></div>
            <p style="color: #1d4ed8; background: rgba(41, 98, 255, 0.08); padding: 12px; border-radius: 4px; font-size: 0.82rem; font-weight: 600; line-height: 1.5; margin-top:14px; margin-bottom:0; border: 1px solid rgba(41, 98, 255, 0.2);">
                💡 <strong>Beta Advantage:</strong> Submitting your active account registration now locks in lifetime terminal analytics components completely free before platform deployment.
            </p>
        </div>
    """), unsafe_allow_html=True)

    email_input = st.text_input(
        "Account Email Access Route",
        label_visibility="collapsed",
        placeholder="Enter email address (e.g. name@company.com)"
    )
    st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)

    if st.button("Claim Premium Terminal Access Token", use_container_width=True):
        if not email_input or "@" not in email_input:
            st.warning("Please provide a valid active email address.")
        else:
            try:
                response = requests.post(
                    'https://formspree.io/f/xqeoyagn',
                    json={'email': email_input},
                    headers={'Accept': 'application/json'}
                )
                if response.status_code == 200:
                    try:
                        conn_sub = sqlite3.connect(DB_PATH)
                        cursor_sub = conn_sub.cursor()
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cursor_sub.execute(
                            "INSERT OR IGNORE INTO beta_subscribers (email, signup_date) VALUES (?, ?)",
                            (email_input.strip().lower(), timestamp)
                        )
                        conn_sub.commit()
                        conn_sub.close()
                    except Exception:
                        pass
                    st.success("🎉 Connection link configured! Your unrestricted access token is live.")
                else:
                    st.error("System sync timed out. Please try hitting the button again.")
            except Exception:
                st.error("Network interface error. Check terminal connections.")

    st.markdown(textwrap.dedent("""
        <div class="review-box" style="margin-top:12px;">
            <div class="star-row">★★★★★</div>
            <p style="margin:0; font-size:0.82rem; color:#334155; font-weight:500; line-height:1.4;">
                "The feed can be really helpful when trying to choose what you want to invest in as it’s current real-time info."
            </p>
            <div style="font-size:0.7rem; color:#64748b; margin-top:4px; font-weight:500;">— Verified Beta Trader</div>
        </div>
    """), unsafe_allow_html=True)


# ==========================================================
# 📖 TERMINAL METHODOLOGY GLOSSARY
# ==========================================================
st.markdown("---")
st.markdown(textwrap.dedent("""
    <div style="padding: 0 max(4vw, 20px); margin-bottom: 2rem;">
        <h4 style="font-weight:700; margin-bottom:12px;">📖 System Metrics Glossary</h4>
        <p style="font-size:0.88rem; line-height:1.6; color:#475569;">
            <strong>Relative Impact Level:</strong> Computed logarithmically against the security's 30-day median trading volume and dollar liquidity structure. An open-market purchase of $1M carries vastly alternative tracking priority inside a mid-cap security versus a mega-cap asset.
        </p>
        <div class="legal-disclaimer-footer">
            <strong>Disclaimer:</strong> Smart Money Radar provides automated raw data ingestion and data visualizations compiled entirely from public SEC algorithmic filings. None of the components structured within this beta terminal serve as customized legal, financial, or personalized investment advisory positions. Past historical insider execution matrices provide no direct absolute future performance certainties.
        </div>
    </div>
"""), unsafe_allow_html=True)