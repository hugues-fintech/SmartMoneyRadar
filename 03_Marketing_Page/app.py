import streamlit as st
import sqlite3
import pandas as pd
import requests
import os
from datetime import datetime

# Set professional layout framework
st.set_page_config(page_title="Smart Money Radar — Insider Tracking Terminal", page_icon="📡", layout="wide")

# ==========================================================
# 🗺️ DYNAMIC PATH RESOLUTION FOR CLOUD DEPLOYMENT
# ==========================================================
# This automatically calculates the correct path to 02_Database 
# whether running locally on Windows or deployed on Linux cloud servers.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "02_Database", "insider_vault.db")

# --- STEP 2 AUTOMATION: INITIALIZE LOCAL SUBSCRIBER TABLE ---
try:
    # Ensure the directory folder structure exists in a cloud container environment
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
    st.error(f"Failed to initialize subscriber database connection: {e}")

# --- TRADING 212 BRAND DESIGN & PREMIUM FRAMING ---
st.markdown("""
    <style>
    /* Global Background and Grid Frame */
    .main { background-color: #fcfdfe; }
    div.block-container { 
        padding: 2.5rem max(2vw, 20px);
        max-width: 1350px; 
    }
    
    /* Institutional Layout Frame */
    .terminal-frame {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 30px;
        margin-bottom: 2rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.01);
    }
    
    /* Logo Header Styling */
    .brand-logo-container {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
    }
    .logo-icon {
        background: #0066cc;
        color: white;
        padding: 6px 10px;
        border-radius: 6px;
        font-weight: 800;
        font-size: 1.1rem;
    }
    .brand-text {
        color: #0066cc;
        font-weight: 800;
        font-size: 1.3rem;
        letter-spacing: 0.02em;
    }
    
    /* Headings */
    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        color: #0f172a;
        line-height: 1.2;
        letter-spacing: -0.02em;
        margin-bottom: 14px;
    }
    .hero-subtitle {
        font-size: 1.1rem;
        color: #475569;
        line-height: 1.6;
        max-width: 1050px;
    }

    /* Counter Blocks */
    .metric-card {
        background: #ffffff;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    .metric-label {
        font-size: 0.78rem;
        color: #64748b;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 4px;
    }
    .metric-val {
        font-size: 1.65rem;
        font-weight: 800;
        color: #0f172a;
    }
    
    /* Signal Cards */
    .signal-card {
        background: #ffffff;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        margin-bottom: 14px;
    }
    
    /* Status Tags */
    .tag-whale {
        background-color: #eff6ff;
        color: #1e40af;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .tag-director {
        background-color: #f0fdf4;
        color: #166534;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    
    /* Tiers Grid Design */
    .tier-grid {
        display: flex;
        gap: 12px;
        margin-top: 14px;
        margin-bottom: 20px;
    }
    .tier-box {
        flex: 1;
        padding: 14px;
        border-radius: 8px;
        font-size: 0.88rem;
    }
    .tier-free {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        color: #475569;
    }
    .tier-premium {
        background: #f0f7ff;
        border: 1px solid #bfdbfe;
        color: #1e3a8a;
    }
    
    /* Sidebar Outer Card */
    .upgrade-card {
        background: #ffffff;
        padding: 32px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 20px rgba(15, 23, 42, 0.02);
    }
    
    /* Custom Input Prompt Label Layout */
    .custom-input-label {
        font-size: 0.95rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 10px;
        margin-top: 20px;
    }
    
    /* Input Field Overrides to force prominent high-contrast blue border */
    div[data-baseweb="input"] {
        border: 2px solid #0066cc !important;
        border-radius: 6px !important;
        background-color: #ffffff !important;
    }
    
    /* Professional High-Contrast Institutional Footer */
    .footer-container {
        margin-top: 6rem;
        padding-top: 30px;
        border-top: 2px solid #e2e8f0;
        text-align: center;
        color: #1e293b;
        font-size: 0.95rem;
        line-height: 1.6;
        font-weight: 700;
    }
    .footer-copyright {
        color: #475569;
        font-size: 0.85rem;
        margin-top: 6px;
        font-weight: 500;
    }
    </style>
""", unsafe_allow_html=True)

# --- BRANDING FRAMEWORK WITH INTEGRATED LOGO ---
st.markdown("""
    <div class="terminal-frame">
        <div class="brand-logo-container">
            <div class="logo-icon">⚡ SMR</div>
            <div class="brand-text">SMART MONEY RADAR</div>
        </div>
        <div class="hero-title">Track Real-Time Corporate Insider Buying.</div>
        <div class="hero-subtitle">
            When public company CEOs, CFOs, and board members deploy substantial sums of their 
            <strong>own personal family capital</strong> into their own stock, they aren't speculating—they are acting on non-public execution visibility. 
            Our automation engine monitors raw SEC Form 4 wires 24/7 to isolate these high-conviction market entries before the broader public takes notice.
        </div>
    </div>
""", unsafe_allow_html=True)

# --- DATABASE INGESTION ---
try:
    conn = sqlite3.connect(DB_PATH)
    total_tracked_df = pd.read_sql_query("SELECT COUNT(*) as total_count, SUM(total_value) as total_val FROM insider_trades", conn)
    total_count = total_tracked_df['total_count'].iloc[0] or 0
    total_val = total_tracked_df['total_val'].iloc[0] or 0
    
    query = """
        SELECT ticker as [Ticker], company as [Company], insider_name as [Insider], 
               position as [Position], total_value as [Total Value], filing_date as [Filing Date]
        FROM insider_trades 
        ORDER BY filing_date DESC, total_value DESC 
        LIMIT 5
    """
    df_signals = pd.read_sql_query(query, conn)
    conn.close()
except Exception:
    df_signals = pd.DataFrame()
    total_count, total_val = 0, 0

# --- DATA SUMMARY ROW ---
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">📊 Raw SEC Wires Ingested</div><div class="metric-val">{total_count} Exec Filings</div></div>', unsafe_allow_html=True)
with col_m2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">💰 Total Tracked Capital Deployed</div><div class="metric-val">${total_val:,.2f}</div></div>', unsafe_allow_html=True)
with col_m3:
    st.markdown('<div class="metric-card"><div class="metric-label">⚡ Live Network Link</div><div class="metric-val" style="color: #02b159;">● Scanner Active</div></div>', unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# --- SPLIT SCREEN FEED ---
col_left, col_right = st.columns([12, 8], gap="large")

with col_left:
    st.markdown('<h3 style="color:#0f172a; font-weight:800; font-size:1.35rem; margin-bottom:4px; letter-spacing:-0.02em; white-space: nowrap;">📡 Public Terminal Live Stream (Top 5 Recent Moves)</h3>', unsafe_allow_html=True)
    st.markdown('<p style="color:#64748b; font-size:0.95rem; margin-bottom:20px;">Real-time view of institutional insiders buying equity shares directly through open public exchanges:</p>', unsafe_allow_html=True)
    
    if not df_signals.empty:
        for idx, row in df_signals.iterrows():
            formatted_cash = f"${row['Total Value']:,.2f}"
            pos = row['Position'].upper()
            
            if any(x in pos for x in ["CEO", "CHIEF EXECUTIVE", "CFO", "CHIEF FINANCIAL", "PRESIDENT", "OFFICER"]):
                badge = '<span class="tag-whale">👑 C-SUITE WHALE TRADE</span>'
                context_msg = "<strong>Analysis:</strong> An executive managing day-to-day corporate operations is deploying massive personal wealth, signaling short-term operational execution metrics are ahead of schedule."
            else:
                badge = '<span class="tag-director">🏛️ BOARD DIRECTOR TRADE</span>'
                context_msg = "<strong>Analysis:</strong> A member of the company's governing Board of Directors has committed capital, reflecting high macro alignment and valuation support."
                
            st.markdown(f"""
                <div class="signal-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <div>
                            <span style="font-weight: 800; font-size: 1.2rem; color: #0f172a; margin-right: 8px;">{row['Ticker']}</span>
                            {badge}
                        </div>
                        <span style="color: #02b159; font-weight: 800; font-size: 1.25rem;">+{formatted_cash}</span>
                    </div>
                    <div style="color: #334155; font-size: 0.95rem; line-height: 1.5; margin-bottom: 8px;">
                        <strong>Company:</strong> {row['Company']}<br>
                        <strong>Purchaser:</strong> {row['Insider']} (<span style="color:#64748b; font-size:0.9rem;">{row['Position']}</span>)
                    </div>
                    <div style="background: #f8fafc; padding: 10px 14px; border-radius: 6px; font-size: 0.88rem; color: #475569; border-left: 4px solid #0066cc;">
                        💡 {context_msg}
                    </div>
                    <div style="margin-top: 10px; color: #94a3b8; font-size: 0.8rem;">SEC Processing Frame: {row['Filing Date']}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Scanner data sync active. Waiting for next live filing packet...")

# COMPACTED BLOCK: Bypasses Streamlit's inner parser cleanly
with col_right:
    sidebar_html = (
        '<div class="upgrade-card" style="padding-bottom: 20px;">'
        '<h3 style="color:#0f172a; font-weight:800; font-size:1.35rem; margin-top:0; margin-bottom:8px; letter-spacing:-0.01em;">&#128274; Access Control Configuration</h3>'
        '<p style="color: #475569; font-size: 0.93rem; line-height: 1.4; margin-bottom: 14px;">Our data loop filters thousands of executive forms daily. Public web connections are restricted to this 5-row rolling preview stream.</p>'
        '<div class="tier-grid">'
        '<div class="tier-box tier-free">'
        '<strong style="color:#0f172a; font-size:0.9rem;">&#128202; PUBLIC MONITOR</strong>'
        '<ul style="margin-top:6px; margin-bottom:0; padding-left:16px; line-height:1.4; color:#64748b; font-size:0.83rem;"><li>Delayed sample feed</li><li>Aggregate volume counters</li><li>Limited historical visibility</li></ul>'
        '</div>'
        '<div class="tier-box tier-premium">'
        '<strong style="color:#1e3a8a; font-size:0.9rem;">&#128640; PREMIUM TERMINAL</strong>'
        '<ul style="margin-top:6px; margin-bottom:0; padding-left:16px; line-height:1.4; color:#1e40af; font-size:0.83rem;"><li>Instant SMS and Email Alerts</li><li>Multi-Director Cluster Signals</li><li>Unrestricted Archive Filter</li></ul>'
        '</div>'
        '</div>'
        '<p style="color: #334155; font-size: 0.92rem; line-height: 1.4; margin-bottom: 5px;">&#128161; <strong>Beta Program Access:</strong> Joining the Premium Beta queue grants you <strong>unrestricted complimentary access</strong> to all Premium Terminal features while our engineering optimization phase is active.</p>'
        '<div class="custom-input-label">Enter your professional email to secure complimentary beta access:</div>'
        '</div>'
    )
    
    st.markdown(sidebar_html, unsafe_allow_html=True)
    
    email_input = st.text_input("Secure Email Entrance", label_visibility="collapsed", placeholder="name@company.com")
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    
    if st.button("Claim Free Premium Beta Access", use_container_width=True):
        if not email_input or "@" not in email_input:
            st.warning("Please provide a valid email connection address.")
        else:
            try:
                response = requests.post(
                    'https://formspree.io/f/xqeoyagn',
                    json={'email': email_input},
                    headers={'Accept': 'application/json'}
                )
                if response.status_code == 200:
                    # --- STEP 2 AUTOMATION: LOG EMAIL LOCALLY ONCE FORMSPREE CONFORMS SUCCESS ---
                    try:
                        conn_sub = sqlite3.connect(DB_PATH)
                        cursor_sub = conn_sub.cursor()
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # INSERT OR IGNORE avoids throwing SQL errors if the same user clicks multiple times
                        cursor_sub.execute("""
                        INSERT OR IGNORE INTO beta_subscribers (email, signup_date)
                        VALUES (?, ?)
                        """, (email_input.strip().lower(), timestamp))
                        
                        conn_sub.commit()
                        conn_sub.close()
                        
                        st.success("🎉 Success! Your complimentary beta spot is logged. Check your inbox.")
                    except Exception as db_err:
                        # Fallback notification: ensures user experiences a win even if local DB locks momentarily
                        st.success("🎉 Success! Your complimentary beta spot is logged. Check your inbox.")
                        st.sidebar.warning(f"Local logging background bypass: {db_err}")
                else:
                    st.error("Submission sync failure. Please retry.")
            except Exception:
                st.error("Network response timeout. Try again.")

# --- PROFESSIONAL INSTITUTIONAL FOOTER ---
st.markdown("""
    <div class="footer-container">
        <strong>SMART MONEY RADAR TERMINAL ENGINE</strong><br>
        Data curated directly from official SEC Electronic Data Gathering, Analysis, and Retrieval (EDGAR) data feeds.<br>
        <div class="footer-copyright">© 2026 Smart Money Radar. All institutional data models and processing loops proprietary. Framework Beta Build.</div>
    </div>
""", unsafe_allow_html=True)