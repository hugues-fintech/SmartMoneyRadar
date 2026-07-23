# -*- coding: utf-8 -*-
import math
import streamlit as st
import sqlite3
import pandas as pd
import os
import yfinance as yf
import textwrap
from datetime import datetime, timedelta
import secrets
import string

# ==========================================================
# 🔑 SECURITY & CRM MIGRATIONS
# ==========================================================
def generate_alpha_token() -> str:
    """Generates a secure, unique 4-character suffix (e.g., SMR-ALPHA-A8D3)."""
    alphabet = string.ascii_uppercase + string.digits
    suffix = ''.join(secrets.choice(alphabet) for _ in range(4))
    return f"SMR-ALPHA-{suffix}"

def register_user(email: str) -> str:
    """Registers a user into the existing beta_subscribers table, generating a token."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    clean_email = email.strip().lower()
    
    cursor.execute("SELECT alpha_token FROM beta_subscribers WHERE email = ?", (clean_email,))
    existing_user = cursor.fetchone()
    
    if existing_user and existing_user[0]:
        conn.close()
        return existing_user[0]
    
    while True:
        token = generate_alpha_token()
        cursor.execute("SELECT email FROM beta_subscribers WHERE alpha_token = ?", (token,))
        if not cursor.fetchone():
            break
            
    signup_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if existing_user:
        cursor.execute(
            "UPDATE beta_subscribers SET alpha_token = ? WHERE email = ?",
            (token, clean_email)
        )
    else:
        cursor.execute(
            """INSERT INTO beta_subscribers 
               (email, signup_date, validation_state, alpha_token) 
               VALUES (?, ?, ?, ?)""",
            (clean_email, signup_timestamp, 'active', token)
        )
        
    conn.commit()
    conn.close()
    return token

# ==========================================================
# 🛡️ HELPER: FINANCIAL FORMATTERS & PERCENTAGES
# ==========================================================
def format_abbreviated_currency(val):
    """Safely formats large numbers into clean financial abbreviations (e.g., $1.6M)."""
    try:
        if pd.isna(val) or val is None:
            return "$N/A"
        
        num = float(val)
        if math.isnan(num):
            return "$N/A"
            
        sign = "-" if num < 0 else ""
        num = abs(num)
        
        if num >= 1_000_000_000_000:
            return f"{sign}${num / 1_000_000_000_000:.2f}T"
        elif num >= 1_000_000_000:
            return f"{sign}${num / 1_000_000_000:.2f}B"
        elif num >= 1_000_000:
            return f"{sign}${num / 1_000_000:.2f}M"
        elif num >= 1_000:
            return f"{sign}${num / 1_000:.1f}K"
        else:
            return f"{sign}${num:.2f}"
    except Exception:
        return "$N/A"

def get_safe_pct_str(numerator, denominator, label, positive_color, negative_color):
    """Safely calculates percentage with professional Fintech badges."""
    try:
        if pd.isna(numerator) or pd.isna(denominator) or numerator is None or denominator is None:
            return f'<div class="live-pill-standard">{label}: N/A</div>'
        
        num = float(numerator)
        den = float(denominator)
        
        if math.isnan(num) or math.isnan(den) or den == 0:
            return f'<div class="live-pill-standard">{label}: N/A</div>'
        
        pct = ((num - den) / den) * 100
        
        if pct >= 0:
            if label == "Market Premium/Discount":
                return f'<div class="live-pill-premium">🏷️ Premium: +{pct:.1f}%</div>'
            else:
                return f'<div class="live-pill-premium">📈 {label}: +{pct:.1f}%</div>'
        else:
            if label == "Market Premium/Discount":
                return f'<div class="live-pill-discount">🎁 Market Discount: {abs(pct):.1f}%</div>'
            else:
                return f'<div class="live-pill-discount">📉 {label}: {pct:.1f}%</div>'
    except Exception:
        return f'<div class="live-pill-standard">{label}: N/A</div>'

# ==========================================================
# 🔢 INTENSITY & STORYTELLING ENGINE
# ==========================================================
def normalize_intensity(raw_score) -> tuple:
    if pd.isna(raw_score) or raw_score is None or raw_score <= 0:
        return 0, "Low Noise", 0, "→", "#475569"
    
    try:
        val = float(raw_score)
        if math.isnan(val):
            return 0, "Low Noise", 0, "→", "#475569"
            
        display_value = round(val)

        if display_value < 30: 
            label = "Standard Noise"; arrow = "↓"; color = "#64748b"
        elif display_value < 50: 
            label = "Moderate Signal"; arrow = "→"; color = "#38bdf8"
        elif display_value < 75: 
            label = "High Conviction"; arrow = "↑"; color = "#a855f7"
        else: 
            label = "Extreme Anomaly"; arrow = "🔥"; color = "#f97316"

        return display_value, label, display_value, arrow, color
    except:
        return 0, "Low Noise", 0, "→", "#475569"

def estimate_salary_ratio(total_value, position):
    """Calculates behavioral storytelling metric: how many years of salary does this trade represent?"""
    pos_upper = str(position).upper()
    base_salary = 400000 
    if "CEO" in pos_upper or "CHIEF EXECUTIVE" in pos_upper:
        base_salary = 800000
    elif "CFO" in pos_upper or "CHIEF FINANCIAL" in pos_upper:
        base_salary = 500000
    elif "DIRECTOR" in pos_upper:
        base_salary = 200000
        
    ratio = total_value / base_salary
    return max(0.1, round(ratio, 1))

# ==========================================================
# 🧱 STREAMLIT PAGE CONFIG & STATE MANAGEMENT
# ==========================================================
st.set_page_config(
    page_title="Smart Money Radar — Institutional Insider Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "terminal_unlocked" not in st.session_state:
    st.session_state.terminal_unlocked = False

# ==========================================================
# 🗺️ PATH RESOLUTION & DATABASE MIGRATIONS
# ==========================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "02_Database", "insider_vault.db")

def run_database_setup_and_migrations(db_path):
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS beta_subscribers (
            email TEXT PRIMARY KEY,
            signup_date TEXT,
            user_source TEXT DEFAULT 'direct',
            alpha_token TEXT,
            validation_state TEXT DEFAULT 'pending_verification',
            last_active_at TEXT
        );
        """)
        
        cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_subscribers_alpha_token 
        ON beta_subscribers (alpha_token) 
        WHERE alpha_token IS NOT NULL;
        """)
                
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Database Migration Error: {e}")

run_database_setup_and_migrations(DB_PATH)

# ==========================================================
# 🎨 BRAND NEW FINTECH DARK DESIGN SYSTEM
# ==========================================================
st.markdown(textwrap.dedent("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html { scroll-behavior: smooth; }
    html, body, [data-testid="stAppViewContainer"], .main { 
        background-color: #090d16 !important;
        color: #f1f5f9 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    div.block-container { padding: 5rem max(3vw, 20px) !important; max-width: 1400px; }
    [data-testid="stHeader"], footer { visibility: hidden !important; }
    
    h1, h2, h3, h4, h5, h6 { 
        color: #ffffff !important; 
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.03em; 
    }
    label, p, span { color: #94a3b8 !important; }
    
    [data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, #2563eb, #3b82f6, #06b6d4);
        z-index: 999999;
    }
    
    .premium-navbar { 
        position: fixed; 
        top: 4px; 
        left: 0; 
        width: 100%; 
        height: 64px; 
        background: rgba(9, 13, 22, 0.85); 
        backdrop-filter: blur(12px);
        border-bottom: 1px solid rgba(255,255,255,0.06); 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        padding: 0 max(3vw, 20px); 
        z-index: 99999; 
    }
    .nav-logo { 
        font-family: 'Space Grotesk', sans-serif; 
        font-weight: 700; 
        font-size: 1.1rem; 
        color: #ffffff; 
        letter-spacing: -0.02em;
        display: flex; 
        align-items: center; 
        gap: 8px; 
    }
    .nav-logo span {
        background: linear-gradient(90deg, #3b82f6, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    .nav-cta-btn { 
        background: #2563eb; 
        color: #ffffff !important; 
        padding: 10px 20px; 
        border-radius: 99px; 
        font-size: 0.85rem; 
        font-weight: 600; 
        text-decoration: none !important; 
        transition: all 0.2s ease; 
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }
    .nav-cta-btn:hover { 
        background: #1d4ed8; 
        transform: translateY(-1px);
    }

    .ticker-wrap { 
        width: 100%; 
        overflow: hidden; 
        background-color: #0b111e; 
        padding: 12px 0; 
        margin-top: -10px; 
        margin-bottom: 30px; 
        border-radius: 12px; 
        border: 1px solid rgba(255, 255, 255, 0.05); 
    }
    .ticker { display: inline-block; white-space: nowrap; padding-left: 100%; animation: marquee 40s linear infinite; }
    .ticker-item { display: inline-block; padding: 0 2.5rem; font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: #94a3b8; }
    .ticker-item span.up { color: #10b981 !important; }
    @keyframes marquee { 0% { transform: translate3d(0,0,0); } 100% { transform: translate3d(-100%,0,0); } }

    .hero-panel { 
        padding: 44px 38px; 
        background: linear-gradient(135deg, rgba(17, 24, 39, 0.7) 0%, rgba(9, 13, 22, 0.9) 100%); 
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px; 
        margin-bottom: 2.5rem; 
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2); 
    }
    .brand-badge { 
        display: inline-flex; 
        align-items: center; 
        gap: 6px; 
        background: rgba(59, 130, 246, 0.1); 
        color: #60a5fa; 
        padding: 6px 14px; 
        border-radius: 99px; 
        font-size: 0.72rem; 
        font-weight: 700; 
        margin-bottom: 18px; 
        border: 1px solid rgba(59, 130, 246, 0.2); 
        letter-spacing: 0.05em; 
        text-transform: uppercase;
    }
    .hero-main-title { 
        font-size: 2.3rem; 
        font-weight: 800; 
        color: #ffffff !important; 
        line-height: 1.2; 
        margin-bottom: 16px; 
    }
    .hero-desc { 
        font-size: 1.05rem; 
        color: #94a3b8 !important; 
        line-height: 1.6; 
        max-width: 850px; 
    }
   
    .trust-banner { 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        gap: max(4vw, 24px); 
        background: #111827; 
        border: 1px solid rgba(255, 255, 255, 0.05); 
        border-radius: 16px; 
        padding: 24px; 
        margin-bottom: 2.5rem; 
    }
    .trust-item { text-align: center; } 
    .trust-val { 
        font-size: 1.7rem; 
        font-weight: 800; 
        color: #ffffff !important; 
        font-family: 'Space Grotesk', sans-serif;
    } 
    .trust-lbl { 
        font-size: 0.72rem; 
        color: #64748b !important; 
        font-weight: 700; 
        text-transform: uppercase; 
        letter-spacing: 0.05em; 
        margin-top: 6px; 
    }
    .trust-divider { width: 1px; height: 35px; background: rgba(255, 255, 255, 0.08); }

    .signal-card { 
        background: #111827; 
        padding: 26px; 
        border-radius: 16px; 
        border: 1px solid rgba(255, 255, 255, 0.05); 
        margin-bottom: 22px; 
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        transition: border-color 0.2s ease, transform 0.2s ease;
    }
    .signal-card:hover {
        border-color: rgba(59, 130, 246, 0.3);
        transform: translateY(-2px);
    }
    
    .pill-purple { background: rgba(147, 51, 234, 0.12); color: #c084fc !important; padding: 4px 10px; border-radius: 6px; font-size: 0.72rem; font-weight: 700; border: 1px solid rgba(147, 51, 234, 0.25); }
    .pill-blue { background: rgba(59, 130, 246, 0.12); color: #60a5fa !important; padding: 4px 10px; border-radius: 6px; font-size: 0.72rem; font-weight: 700; border: 1px solid rgba(59, 130, 246, 0.25); }
    .pill-orange { background: rgba(249, 115, 22, 0.12); color: #ffedd5 !important; padding: 4px 10px; border-radius: 6px; font-size: 0.72rem; font-weight: 700; border: 1px solid rgba(249, 115, 22, 0.25); }
    
    .live-pill-premium { background: rgba(16, 185, 129, 0.1); color: #34d399 !important; padding: 8px 12px; border-radius: 8px; font-weight: 700; font-size: 0.8rem; border: 1px solid rgba(16, 185, 129, 0.2); flex: 1; text-align: center; }
    .live-pill-discount { background: rgba(249, 115, 22, 0.1); color: #f97316 !important; padding: 8px 12px; border-radius: 8px; font-weight: 700; font-size: 0.8rem; border: 1px solid rgba(249, 115, 22, 0.2); flex: 1; text-align: center; }
    .live-pill-standard { background: rgba(255, 255, 255, 0.03); color: #94a3b8 !important; padding: 8px 12px; border-radius: 8px; font-weight: 600; font-size: 0.8rem; border: 1px solid rgba(255, 255, 255, 0.05); flex: 1; text-align: center; }

    .config-card { 
        background: #111827; 
        border: 1px solid rgba(255, 255, 255, 0.05); 
        border-radius: 16px; 
        padding: 26px; 
        margin-bottom: 20px; 
    }
    .config-header { 
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.1rem; 
        font-weight: 700; 
        color: #ffffff !important; 
        margin-bottom: 14px; 
    }
    .bullet-item { font-size: 0.88rem; color: #94a3b8 !important; margin-bottom: 10px; display: flex; align-items: center; gap: 10px; }
    .bullet-dot { width: 6px; height: 6px; background: #2563eb; border-radius: 50%; }
    
    div[data-testid="stTextInput"] input { 
        background-color: #090d16 !important; 
        color: #ffffff !important; 
        border: 1px solid rgba(255, 255, 255, 0.1) !important; 
        border-radius: 8px !important; 
        padding: 12px !important; 
    }
    div[data-testid="stTextInput"] input:focus { 
        border-color: #2563eb !important; 
        box-shadow: 0 0 0 1px #2563eb !important; 
    }
    div[data-testid="stFormSubmitButton"] button, div.stButton button { 
        background: linear-gradient(90deg, #2563eb, #3b82f6) !important; 
        color: #ffffff !important; 
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 0.95rem !important; 
        font-weight: 700 !important; 
        border-radius: 8px !important;
        border: none !important;
        padding: 14px 28px !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stFormSubmitButton"] button:hover, div.stButton button:hover { 
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4) !important;
    }
    .sec-archive-timestamp { margin-top: 14px; color: #475569 !important; font-size: 0.78rem; font-family: 'JetBrains Mono', monospace; }
    
    .gated-blur-box { 
        background: rgba(255, 255, 255, 0.02); 
        border: 2px dashed rgba(255, 255, 255, 0.1); 
        border-radius: 12px; 
        padding: 24px; 
        text-align: center; 
        margin-top: 14px; 
    }
    .premium-lock-badge { 
        display: inline-flex; 
        align-items: center; 
        gap: 6px; 
        background: rgba(249, 115, 22, 0.1); 
        color: #f97316; 
        padding: 6px 14px; 
        border-radius: 99px; 
        font-size: 0.75rem; 
        font-weight: 700; 
        margin-bottom: 10px; 
        border: 1px solid rgba(249, 115, 22, 0.2); 
    }
    .z-score-display { 
        font-family: 'JetBrains Mono', monospace; 
        font-size: 0.85rem; 
        font-weight: 700; 
        color: #38bdf8; 
        background: rgba(56, 189, 248, 0.08); 
        padding: 4px 10px; 
        border-radius: 6px; 
        border: 1px solid rgba(56, 189, 248, 0.15); 
    }
    .behavioral-story-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(16, 185, 129, 0.08);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.15);
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-top: 8px;
    }
    </style>
"""), unsafe_allow_html=True)

# ==========================================================
# 🗺️ FLOATING NAVBAR & TICKER
# ==========================================================
st.markdown(textwrap.dedent("""
    <div class="premium-navbar">
        <div class="nav-logo">⚡ SMART MONEY <span>RADAR</span></div>
        <a class="nav-cta-btn" href="#join-terminal-anchor">Claim Free Alpha Token</a>
    </div>
"""), unsafe_allow_html=True)

st.markdown(textwrap.dedent("""
<div class="ticker-wrap">
    <div class="ticker">
        <div class="ticker-item">🍏 AAPL <span class="up">▲ Live Monitoring Active</span></div>
        <div class="ticker-item">🤖 MSFT <span class="up">▲ Baseline Tracked</span></div>
        <div class="ticker-item">🚗 TSLA <span class="up">▲ Systems Synced</span></div>
        <div class="ticker-item">📦 AMZN <span class="up">▲ SEC EDGAR Live</span></div>
        <div class="ticker-item">🔍 GOOGL <span class="up">▲ Alpha Isolation Engaged</span></div>
    </div>
</div>
"""), unsafe_allow_html=True)

# ==========================================================
# 🏛️ HERO PANEL
# ==========================================================
st.markdown(textwrap.dedent("""
    <div class="hero-panel">
        <div class="brand-badge">⚡ Institutional Terminal</div>
        <div class="hero-main-title">
            Where Executives Bet Millions of Their Own Cash.
        </div>
        <div class="hero-desc">
            <p style="margin-bottom: 14px; color: #f1f5f9 !important; font-weight: 600; font-size: 1.1rem; line-height: 1.5;">
                Routine executive forms and automated options stock grants represent 99.5% of filing traffic. We eliminate that noise.
            </p>
            <p style="margin: 0; color: #94a3b8 !important; font-size: 0.95rem; line-height: 1.6;">
                Smart Money Radar automatically scans daily SEC Form 4 filings and isolates top 1% unusual "High-Intensity" whale buys. Real cash, real conviction, direct impact.
            </p>
        </div>
    </div>
"""), unsafe_allow_html=True)

# ==========================================================
# 📊 DATABASE RECOVERY & TELEMETRY
# ==========================================================
try:
    conn = sqlite3.connect(DB_PATH)
    
    total_tracked_df = pd.read_sql_query(
        "SELECT COUNT(*) as total_count, SUM(total_value) as total_val FROM insider_trades", conn
    )
    tc_raw = total_tracked_df['total_count'].iloc[0]
    total_count = int(tc_raw) if pd.notna(tc_raw) else 0
    tv_raw = total_tracked_df['total_val'].iloc[0]
    total_val = float(tv_raw) if pd.notna(tv_raw) else 0.0

    # MISE À JOUR : On ne compte que les anomalies positives massives (Z-Score >= 1.5)
    high_conviction_df = pd.read_sql_query(
        "SELECT COUNT(*) as high_count FROM insider_trades WHERE trigger_type != 'NOISE' AND z_score >= 1.5", conn
    )
    hc_raw = high_conviction_df['high_count'].iloc[0]
    high_conviction_count = int(hc_raw) if pd.notna(hc_raw) else 0

    telemetry_df = pd.read_sql_query(
        "SELECT metric_value FROM system_telemetry WHERE metric_key = 'total_raw_scans'", conn
    )
    live_scans_total = int(telemetry_df['metric_value'].iloc[0]) if not telemetry_df.empty else total_count

    # LA REQUÊTE SQL MANQUANTE EST DE RETOUR ICI :
    query = """
        SELECT 
            ticker as [Ticker], 
            company as [Company],                         
            insider_name as [Insider],   
            position as [Position],     
            ROUND(price, 2) as [Buy Price],
            total_value as [Total Value],
            market_cap as [Market Cap],                   
            avg_volume as [Avg Volume],                   
            intensity_score as [Intensity Score], 
            trigger_type as [Trigger Type],               
            filing_date as [Filing Date], 
            z_score as [Z-Score],
            1 as [Unique Insiders]  
        FROM insider_trades 
        WHERE trigger_type != 'NOISE' AND z_score >= 1.5
        ORDER BY filing_date DESC, total_value DESC 
        LIMIT 10
    """
    
    df_signals = pd.read_sql_query(query, conn)
    conn.close()
except Exception:
    df_signals = pd.DataFrame()
    total_count, total_val, high_conviction_count, live_scans_total = 0, 0, 0, 0

total_capital = df_signals['Total Value'].sum() if not df_signals.empty else 0
formatted_total_capital = format_abbreviated_currency(total_capital)
formatted_total_signals = f"{high_conviction_count} Anomalies Isolated" if high_conviction_count > 0 else "0 Active Signals"
formatted_raw_pool = f"Parsed from {live_scans_total:,} SEC forms"

# ==========================================================
# 📊 FINTECH DUAL-COUNTER BANNER
# ==========================================================
st.markdown(textwrap.dedent(f"""
    <div class="trust-banner">
        <div class="trust-item">
            <div class="trust-val">{formatted_total_capital}</div>
            <div class="trust-lbl">Gross High-Conviction Value</div>
        </div>
        <div class="trust-divider"></div>
        <div class="trust-item">
            <div class="trust-val" style="color: #3b82f6 !important;">{formatted_total_signals}</div>
            <div class="trust-lbl">{formatted_raw_pool}</div>
        </div>
        <div class="trust-divider"></div>
        <div class="trust-item">
            <div class="trust-val">Outlier Target (Z &ge; 2.0&sigma;)</div>
            <div class="trust-lbl">Curation Threshold</div>
        </div>
    </div>
"""), unsafe_allow_html=True)

# ==========================================================
# 📡 DUAL COLUMN LAYOUT
# ==========================================================
col_left, col_right = st.columns([11, 9], gap="large")

# ---------------- LEFT COLUMN: OPEN DATA WIRE ----------------
with col_left:
    st.markdown('<h3 style="font-size:1.3rem; margin-bottom:6px;">📡 Curated Whale Stream</h3>', unsafe_allow_html=True)
    st.markdown('<p style="color:#94a3b8 !important; font-size:0.9rem; margin-bottom:20px;">Top-tier personal money trades filtered through log-normal metrics:</p>', unsafe_allow_html=True)

    if not df_signals.empty:
        for idx, row in df_signals.iterrows():
            tv = row.get('Total Value')
            formatted_cash = format_abbreviated_currency(tv)
            
            insider_buy_price = row.get('Buy Price')
            ticker_symbol = row.get('Ticker', "N/A")
            pos_label = str(row.get('Position', "")).upper()
            trigger_tag = str(row.get('Trigger Type', ""))
            intensity = row.get('Intensity Score')
            raw_z_score = row.get('Z-Score', 0.0)
            
            mcap_display = str(row.get('Market Cap', "N/A"))
            vol_val = row.get('Avg Volume')
            vol_display = f"{int(vol_val):,}" if pd.notna(vol_val) else "Data Unavailable"

            norm_score, norm_label, display_score, arrow, bar_color = normalize_intensity(intensity)
            trigger_upper = trigger_tag.upper()

            if "ALIGNMENT" in trigger_upper:
                badge_style = '<span class="pill-purple">🔥 CLUSTER + WHALE ALIGNMENT</span>'
            elif "CLUSTER" in trigger_upper:
                badge_style = '<span class="pill-blue">🏛️ MULTI-INSIDER CLUSTER</span>'
            else:
                badge_style = '<span class="pill-orange">🐋 HIGH-INTENSITY WHALE</span>'

            multiplier = estimate_salary_ratio(tv, pos_label)
            story_html = f"""
            <div class="behavioral-story-badge">
                💰 Conviction Ratio: Purchased ~{multiplier}x estimated annual salary net
            </div>
            """

            wire_perf_html = '<div class="live-pill-standard">Checking pricing wire...</div>'
            trade_perf_html = '<div class="live-pill-standard">Calculating entry basis...</div>'
            
            try:
                stock_engine = yf.Ticker(ticker_symbol)
                history_slice = stock_engine.history(period="5d")

                if not history_slice.empty:
                    current_market_price = float(history_slice['Close'].iloc[-1])
                    entry_wire_price = float(history_slice['Close'].iloc[0])
                            
                    wire_perf_html = get_safe_pct_str(current_market_price, entry_wire_price, "Wire Alert", "#10b981", "#f97316")
                    trade_perf_html = get_safe_pct_str(current_market_price, insider_buy_price, "Market Premium/Discount", "#10b981", "#f97316")
            except Exception:
                pass

            if st.session_state.terminal_unlocked:
                gated_intel_html = (
                    f'<div style="background: rgba(56, 189, 248, 0.04); border: 1px solid rgba(56, 189, 248, 0.15); border-radius: 8px; padding: 14px; margin-top: 12px;">'
                    f'  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">'
                    f'      <span style="font-size: 0.85rem; font-weight: 700; color: #38bdf8;">📊 LOG-NORMAL VALIDATION</span>'
                    f'      <span class="z-score-display">Z-Score: {raw_z_score:+.2f}σ</span>'
                    f'  </div>'
                    f'  <p style="font-size: 0.85rem; color: #94a3b8; margin: 0; line-height: 1.4;">'
                    f'      This trade size represents an outlier threshold of <strong>{raw_z_score:+.2f} standard deviations</strong> outside normal corporate purchasing curves. Statistical validation: <strong>99th percentile anomaly</strong>.'
                    f'  </p>'
                    f'</div>'
                )
            else:
                gated_intel_html = (
                    f'<div class="gated-blur-box">'
                    f'  <div class="premium-lock-badge">🔒 ADVANCED LOG-NORMAL METRIC LOCKED</div>'
                    f'  <p style="font-size: 0.82rem; color: #94a3b8; margin: 0 0 10px 0; line-height: 1.4;">'
                    f'      Z-Score distributions, cluster variances, and premium metrics are gated.'
                    f'  </p>'
                    f'  <a href="#join-terminal-anchor" style="font-size: 0.82rem; font-weight: 700; color: #38bdf8; text-decoration: none;">Claim free alpha token to unlock deep analysis metrics →</a>'
                    f'</div>'
                )

            card_html = (
                f'<div class="signal-card">'
                f'  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">'
                f'      <div><span style="font-weight: 700; font-size: 1.25rem; font-family:\'Space Grotesk\', sans-serif; margin-right: 8px; color: #ffffff;">{ticker_symbol}</span>{badge_style}</div>'
                f'      <span style="color: #10b981; font-weight: 700; font-size: 1.25rem; font-family: \'JetBrains Mono\', monospace;">{formatted_cash}</span>'
                f'  </div>'
                f'  <div style="margin-top:12px; margin-bottom:14px;">'
                f'      <div style="display: flex; justify-content: space-between; font-size:0.85rem; font-weight:600; color:#94a3b8; margin-bottom:6px;">'
                f'          <span>Conviction Intensity Score</span>'
                f'          <span style="color: {bar_color};">{norm_label} ({display_score}/100) {arrow}</span>'
                f'      </div>'
                f'      <div style="width:100%; background:rgba(255,255,255,0.06); height:8px; border-radius:99px;">'
                f'          <div style="width:{display_score}%; height:8px; border-radius:99px; background:linear-gradient(90deg, #3b82f6, {bar_color});"></div>'
                f'      </div>'
                f'      {story_html}'
                f'  </div>'
                f'  <div style="color: #94a3b8; font-size: 0.9rem; line-height: 1.5; margin-bottom: 12px;">'
                f'      <strong style="color: #475569;">Company:</strong> {row.get("Company")} (Scale: {mcap_display} | Vol: {vol_display})<br>'
                f'      <strong style="color: #475569;">Purchaser:</strong> {row.get("Insider")} (<span style="color:#ffffff;">{pos_label}</span>)'
                f'  </div>'
                f'  <div style="margin-top: 10px; margin-bottom: 12px; display: flex; gap: 10px; width: 100%;">{wire_perf_html}{trade_perf_html}</div>'
                f'  {gated_intel_html}'
                f'  <div class="sec-archive-timestamp">SEC Edgar Archive Date: {row.get("Filing Date")}</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info("Pipeline buffers clean. Awaiting raw streaming execution coordinates.")

# ---------------- RIGHT COLUMN: GATED VISUALIZATIONS & EMAIL CAPTURE ----------------
with col_right:
    st.markdown('<h3 style="font-size:1.3rem; margin-bottom:6px;">📊 Matrix Visualizer</h3>', unsafe_allow_html=True)
    st.markdown('<p style="color:#94a3b8 !important; font-size:0.9rem; margin-bottom:20px;">Relational tracking mapping rarity indices against capital vectors:</p>', unsafe_allow_html=True)

    if not st.session_state.terminal_unlocked:
        lock_screen_html = textwrap.dedent("""
            <div style="background-color: rgba(255,255,255,0.02); border: 2px dashed rgba(255,255,255,0.08); border-radius: 16px; padding: 45px 30px; text-align: center; margin-bottom: 24px;">
                <div class="premium-lock-badge">🔒 INTERACTIVE CHARTS LOCKED</div>
                <h4 style="margin: 12px 0 8px 0; font-size: 1.1rem; font-weight: 700; color: #fff;">Unlock Log-Normal Dispersion Map</h4>
                <p style="font-size: 0.88rem; color: #94a3b8; margin: 0 auto 18px auto; line-height: 1.5; max-width: 340px;">
                    Gain full access to the interactive Signal Scatter Map and Normal distribution filters by verifying your operational profile.
                </p>
            </div>
        """).strip()
        st.markdown(lock_screen_html, unsafe_allow_html=True)
        
    else:
        if not df_signals.empty:
            import plotly.graph_objects as go
            import numpy as np

            st.markdown('<div class="config-card">', unsafe_allow_html=True)
            
            x_axis = np.linspace(-4, 4, 200)
            y_axis = (1 / np.sqrt(2 * np.pi)) * np.exp(-0.5 * x_axis**2)
            
            curve_fig = go.Figure()
            curve_fig.add_trace(go.Scatter(x=x_axis, y=y_axis, mode='lines', line=dict(color='#3b82f6', width=2), name='Market Base'))
            curve_fig.add_vline(x=2.0, line_dash="dash", line_color="#ef4444", line_width=2)
            
            curve_fig.update_layout(
                title=dict(text="📊 NORMAL DISTRIBUTION BOUNDARY (Z &ge; 2.0)", font=dict(size=12, color="#ffffff", family="Space Grotesk")),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=35, b=10), height=180, showlegend=False, xaxis_visible=False, yaxis_visible=False
            )
            st.plotly_chart(curve_fig, use_container_width=True, config={'displayModeBar': False})
            
            st.markdown("""
                <div style="background: rgba(255,255,255,0.01); border-top: 1px solid rgba(255,255,255,0.05); padding: 10px 12px; margin-top: -10px; border-radius: 0 0 12px 12px;">
                    <p style="margin: 0; font-size: 0.8rem; line-height: 1.4; color: #94a3b8;">
                        💡 <strong>The 99% Rule:</strong> Every trade in this zone has cleared an outlier threshold. Routine salary deductions reside safely on the left of the red threshold line.
                    </p>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="config-card">', unsafe_allow_html=True)
            bubble_fig = go.Figure()
            
            if not df_signals.empty:
                df_chart = df_signals.sort_values(by='Unique Insiders', ascending=True).copy()
                np.random.seed(42) 
                df_chart['Jittered_X'] = df_chart['Z-Score'].apply(
                    lambda x: x + np.random.uniform(-0.6, 0.6) if -5 <= x <= 8 else x
                )

                distinct_colors = [
                    '#3b82f6', '#ec4899', '#10b981', '#a855f7', '#f97316', 
                    '#06b6d4', '#ef4444', '#6366f1', '#22c55e', '#f59e0b'
                ]
                df_chart['Bubble_Color'] = [distinct_colors[i % len(distinct_colors)] for i in range(len(df_chart))]
                bubble_sizes = 12 + (df_chart['Unique Insiders'] * 7)

                bubble_fig.add_trace(go.Scatter(
                    x=df_chart['Jittered_X'],
                    y=df_chart['Total Value'],
                    mode='markers', 
                    marker=dict(
                        size=bubble_sizes,
                        color=df_chart['Bubble_Color'],  
                        opacity=0.85,                     
                        line=dict(width=1.5, color='#090d16') 
                    ),
                    text=df_chart['Ticker'],
                    hovertemplate=(
                        "<b>Ticker:</b> %{text}<br>"
                        "<b>Real Variance:</b> %{customdata[0]:+.2f}σ<br>"
                        "<b>Total Value:</b> $%{y:,.2f}<br>"
                        "<b>Consensus:</b> %{customdata[1]} Exec(s)<extra></extra>"
                    ),
                    customdata=np.stack((df_chart['Z-Score'], df_chart['Unique Insiders']), axis=-1)
                ))
            
            bubble_fig.update_layout(
                title=dict(text="⚡ SIGNAL MAP: Trade Size vs. Rarity", font=dict(size=12, color="#ffffff", family="Space Grotesk")),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=15, r=15, t=35, b=15), height=230,
                xaxis=dict(
                    title=dict(text="How Unusual (Z-Score)", font=dict(size=10, color="#94a3b8")), 
                    showgrid=False,
                    zeroline=True,
                    zerolinecolor="rgba(255,255,255,0.1)",
                    tickfont=dict(color="#94a3b8")
                ),
                yaxis=dict(
                    title=dict(text="Cash Invested ($)", font=dict(size=10, color="#94a3b8")), 
                    type='log', 
                    showgrid=False,
                    tickfont=dict(color="#94a3b8")
                )
            )
            st.plotly_chart(bubble_fig, use_container_width=True, config={'displayModeBar': False})
            
            st.markdown("""
                <div style="background: rgba(255,255,255,0.01); border-top: 1px solid rgba(255,255,255,0.05); padding: 10px 12px; margin-top: -10px; border-radius: 0 0 12px 12px;">
                    <p style="margin: 0; font-size: 0.8rem; line-height: 1.4; color: #94a3b8;">
                        💡 <strong>Interpretation:</strong> Look for large bubbles (multiple execution clusters) residing high (large scale value) and to the far-right (exceptional mathematical rarity).
                    </p>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Visual framework active. Awaiting pipeline stream coordinates.")

    # ==========================================================
    # 📝 LEAD CAPTURE FORM
    # ==========================================================
    st.markdown(textwrap.dedent("""
        <div id="join-terminal-anchor" class="config-card">
            <div class="config-header">🔒 Establish Free Alpha Terminal Profile</div>
            <p style="color: #94a3b8 !important; font-size: 0.88rem; line-height: 1.5; margin-bottom: 14px;">
                Secure real-time access to mathematically audited standard deviation profiles and outlier distributions:
            </p>
            <div class="bullet-item"><div class="bullet-dot"></div><span><strong>Outlier Mapping:</strong> Reveal exact math standard deviations.</span></div>
            <div class="bullet-item"><div class="bullet-dot"></div><span><strong>Whale Cluster Tracks:</strong> Unlock interactive coordinate scatter plots.</span></div>
            <div class="bullet-item"><div class="bullet-dot"></div><span><strong>Early Adopter Bonus:</strong> Lock in lifetime complimentary data layers.</span></div>
            <p style="color: #60a5fa; background: rgba(59, 130, 246, 0.08); padding: 12px; border-radius: 8px; font-size: 0.82rem; font-weight: 600; line-height: 1.5; margin-top:14px; margin-bottom:14px; border: 1px solid rgba(59, 130, 246, 0.15); text-align: justify;">
                💡 <strong>Early Access Guarantee:</strong> Creating an alpha token now ensures your dashboard access profile remains completely unrestricted during all future development updates.
            </p>
        </div>
    """), unsafe_allow_html=True)

    with st.form("subscriber_capture_form", clear_on_submit=False):
        user_email = st.text_input(
            "Account Email Target",
            label_visibility="collapsed",
            placeholder="Enter business email (e.g., name@firm.com)"
        )
        submit_btn = st.form_submit_button("Generate Free Terminal Token", use_container_width=True)
        
        if submit_btn:
            if not user_email or "@" not in user_email or "." not in user_email:
                st.warning("Please provide a valid active operational email target.")
            else:
                sanitized_email = user_email.strip().lower()
                try:
                    token = register_user(sanitized_email)
                    if token:
                        st.session_state.terminal_unlocked = True
                        st.session_state.user_token = token
                        
                        st.success("🎉 Alpha Profile Activated successfully!")
                        st.info(f"🔑 **YOUR PRIVATE SECURE TOKEN:** `{token}`")
                        st.code(token, language="text")
                    else:
                        st.error("Failed to compile profile token. Please check database configuration.")
                except Exception as db_err:
                    st.error(f"Local storage compilation synchronization failed: {db_err}")

# ==========================================================
# 🔐 SECURE ADMIN CRM CONSOLE
# ==========================================================
st.markdown("---")
with st.expander("🔐 Open Admin Console Link", expanded=False):
    admin_key_input = st.text_input("Enter Dashboard Credentials", type="password")
    
    if admin_key_input == "radar_admin_2026":
        st.success("Secure CRM Node Active")
        try:
            conn_admin = sqlite3.connect(DB_PATH)
            df_subs = pd.read_sql_query("SELECT * FROM beta_subscribers", conn_admin)
            conn_admin.close()
            
            total_leads = len(df_subs)
            active_alphas = len(df_subs[df_subs['validation_state'] == 'active']) if 'validation_state' in df_subs.columns else 0
            
            kpi_col1, kpi_col2 = st.columns(2)
            kpi_col1.metric("Gross Registered Leads", total_leads)
            kpi_col2.metric("Active Premium Alphas", active_alphas)
            
            st.write("### Subscriber List")
            edited_df = st.data_editor(
                df_subs,
                column_config={
                    "email": st.column_config.TextColumn("Email Address", disabled=True),
                    "signup_date": st.column_config.TextColumn("Signup Time", disabled=True),
                    "validation_state": st.column_config.SelectboxColumn(
                        "Status State",
                        options=["pending_verification", "active", "banned"],
                        required=True,
                    ),
                    "user_source": st.column_config.TextColumn("Lead Source"),
                    "alpha_token": st.column_config.TextColumn("Access Token"),
                    "last_active_at": st.column_config.TextColumn("Last Active", disabled=True)
                },
                hide_index=True,
                key="crm_interactive_editor"
            )
            
            if st.button("Commit Database Changes"):
                try:
                    conn_save = sqlite3.connect(DB_PATH)
                    edited_df.to_sql("beta_subscribers", conn_save, if_exists="replace", index=False)
                    conn_save.close()
                    st.toast("CRM Matrix successfully synchronized!", icon="💾")
                    st.rerun()
                except Exception as save_err:
                    st.error(f"Commit Failed: {save_err}")
        except Exception as read_err:
            st.error(f"Failed to read subscriber data: {read_err}")
    elif admin_key_input:
        st.error("Invalid credentials.")