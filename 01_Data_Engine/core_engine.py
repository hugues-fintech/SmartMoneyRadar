import os
import sqlite3
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from edgar import set_identity, get_filings

# ==========================================================
# 🛡️ 1. SEC IDENTITY & SECURE CONFIGURATION
# ==========================================================
# Identité anonymisée pour protéger ton profil professionnel
set_identity("Smart Money Radar admin@smartmoneyradar.com")

# Les clés sont maintenant appelées depuis l'environnement du système (invisibles dans le code)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
DASHBOARD_URL = "https://smart-money-radar.streamlit.app" # Ton lien public

def send_telegram_alert(ticker, trigger_type, score, insider, position, value, z_score):
    """Envoie l'alerte sur Telegram de manière sécurisée."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("    [!] Telegram tokens missing in environment. Alert not sent.")
        return

    # Nettoyage des décimales pour le score de conviction
    clean_score = round(float(score), 1)

    emoji = "🔥" if "ALIGNMENT" in trigger_type else ("🐋" if "WHALE" in trigger_type else "🏛️")
    
    message = (
        f"{emoji} **SMART MONEY RADAR SIGNAL: {trigger_type}**\n\n"
        f"📈 **Ticker:** ${ticker}\n"
        f"👤 **Insider:** {insider} ({position})\n"
        f"💰 **Transaction Value:** ${value:,.2f}\n"
        f"📊 **Log-Normal Deviation:** {z_score:+.2f}σ\n"
        f"🎯 **Conviction Score:** {clean_score}/100\n\n"
        f"🔗 [View Full Intelligence Dashboard]({DASHBOARD_URL})"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"    [!] Telegram Dispatch Failed: {e}")

# ==========================================================
# 📂 2. DYNAMIC PATH MAPPING & DATABASE
# ==========================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "02_Database", "insider_vault.db")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

db_connection = sqlite3.connect(DB_PATH)
cursor = db_connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS insider_trades (
    filing_id TEXT PRIMARY KEY,
    ticker TEXT,
    company TEXT,
    insider_name TEXT,
    position TEXT,
    shares INTEGER,
    shares_after INTEGER,
    price REAL,
    total_value REAL,
    market_cap TEXT,
    avg_volume INTEGER,
    intensity_score REAL,
    trigger_type TEXT,
    filing_date TEXT,
    z_score REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS system_telemetry (
    metric_key TEXT PRIMARY KEY,
    metric_value INTEGER
)
""")
cursor.execute("INSERT OR IGNORE INTO system_telemetry VALUES ('total_raw_scans', 0)")
db_connection.commit()

def fetch_ticker_market_context(ticker):
    """Retrieves real-time context from Yahoo Finance safely."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        mcap = info.get('marketCap') or info.get('enterpriseValue')
        vol = info.get('averageVolume') or info.get('volume')
        return (mcap if mcap and mcap > 0 else None, vol if vol and vol > 0 else None)
    except Exception:
        return None, None

def calculate_log_normal_z_score(ticker, current_value):
    """Computes Z-Score relative to ticker history."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty or len(hist) < 20:
            return 0.0
        
        historical_dollar_volumes = hist['Volume'] * hist['Close']
        historical_dollar_volumes = historical_dollar_volumes[historical_dollar_volumes > 0]
        
        log_volumes = np.log(historical_dollar_volumes)
        mu_log = log_volumes.mean()
        sigma_log = log_volumes.std()
        
        if sigma_log == 0:
            return 0.0
            
        current_log_val = np.log(current_value) if current_value > 0 else 0
        z_score = (current_log_val - mu_log) / sigma_log
        return float(z_score)
    except Exception:
        return 0.0

# ==========================================================
# 🚀 3. CORE ENGINE LOOP
# ==========================================================
print("==========================================================")
print(" 🚀 ENGINE ACTIVE: FETCHING SEC EDGAR STREAMS")
print("==========================================================")
try:
    filing_buffer = get_filings(form="4")
    recent_filings = filing_buffer.latest(100)
    all_purchases = []
    print(f"[*] Extracting metrics from {len(recent_filings)} forms...")
except Exception as e:
    print(f"❌ Connection Interrupted: {e}")
    exit()

for index, filing in enumerate(recent_filings):
    print(f"    ⏳ Parsing filing [{index+1}/{len(recent_filings)}]...", end="\r")
    try:
        form4_data = filing.obj()
        if form4_data is None: 
            continue
        
        df_raw = form4_data.to_dataframe()
        ticker = getattr(filing, 'ticker', None)
        if not ticker or str(ticker).lower() in ['none', 'nan']:
            ticker_cols = [c for c in df_raw.columns if 'ticker' in c.lower()]
            if ticker_cols:
                ticker = str(df_raw[ticker_cols[0]].iloc[0]).upper()
        
        # FIX 1: Alignement corrigé pour le bloc de validation du ticker
        if not ticker or ticker in ["UNKNOWN", "NONE", "NULL", "N/A"]:
            continue
            
        df_buys = df_raw[(df_raw['Transaction Type'].str.lower() == 'purchase') | (df_raw['Code'].str.upper() == 'P')].copy()
        
        for i, row in df_buys.iterrows():
            val = float(row.get('Value', 0) or (float(row['Shares']) * float(row['Price'])))
            shares_owned_after = float(row.get('Shares Owned After', 0) or 0)
            
            all_purchases.append({
                'filing_id': f"{filing.accession_number}_{i}",
                'Ticker': ticker,
                'Company': row.get('Issuer', filing.company),
                'Insider': row.get('Insider', 'Unknown'),
                'Position': str(row.get('Position', '')).upper(),
                'Shares': int(row['Shares']),
                'SharesAfter': shares_owned_after,
                'Price': float(row['Price']),
                'Value': val,
                'Date': str(filing.filing_date)
            })
    except Exception:
        continue

print("\n✅ SEC Parsing complete. Starting context resolution...")

if all_purchases:
    df_master = pd.DataFrame(all_purchases)
    unique_tickers = df_master['Ticker'].unique()
    
    market_context_cache = {}
    for t_idx, t in enumerate(unique_tickers):
        print(f"    📊 API Lookup [{t_idx+1}/{len(unique_tickers)}]: {t}...", end="\r")
        market_context_cache[t] = fetch_ticker_market_context(t)
        time.sleep(1.5) # PAUSE DE SÉCURITÉ: Prévient le bannissement par Yahoo Finance
    
    print("\n💾 Processing database injections and calculations...")
    new_records_saved = 0
    
    for _, row in df_master.iterrows():
        ticker_symbol = row['Ticker']
        val = row['Value']
        current_date_str = row['Date']
        
        t_ctx = market_context_cache.get(ticker_symbol, (None, None))
        mcap, avg_vol = t_ctx[0], t_ctx[1]
        
        calculated_z = calculate_log_normal_z_score(ticker_symbol, val)

        cursor.execute("""
            SELECT DISTINCT insider_name FROM insider_trades 
            WHERE ticker = ? 
            AND ABS(strftime('%s', filing_date) - strftime('%s', ?)) <= (3 * 86400)
        """, (ticker_symbol, current_date_str))
        cluster_insiders = {r[0] for r in cursor.fetchall()}
        cluster_insiders.add(row['Insider'])
        cluster_count = len(cluster_insiders)

        if calculated_z >= 2.0:
            intensity_score = min(80.0 + (calculated_z - 2.0) * 5.0, 100.0)
            trigger_type = "🔥 CLUSTER + WHALE ALIGNMENT" if cluster_count >= 2 else "🐋 HIGH-INTENSITY WHALE"
        # FIX 2: Alignement corrigé pour les variables sous le bloc cluster_count >= 2
        elif cluster_count >= 2:
            intensity_score = round(50.0 + min(float(cluster_count) * 10.0, 30.0), 1)
            trigger_type = "🏛️ MULTI-INSIDER CLUSTER"
        else:
            intensity_score = max(5.0, round(25.0 + (calculated_z * 10.0), 2))
            trigger_type = "NOISE"

        mcap_value = int(mcap) if mcap else None
        
        # On vérifie si l'enregistrement est complètement NOUVEAU
        cursor.execute("SELECT filing_id FROM insider_trades WHERE filing_id = ?", (row['filing_id'],))
        is_new = cursor.fetchone() is None

        cursor.execute("""
            INSERT OR REPLACE INTO insider_trades 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (row['filing_id'], ticker_symbol, row['Company'], row['Insider'], row['Position'], 
              row['Shares'], row['SharesAfter'], row['Price'], val, mcap_value, 
              avg_vol, intensity_score, trigger_type, current_date_str, round(calculated_z, 4)))
        
        if is_new:
            new_records_saved += 1
            if trigger_type != "NOISE":
                print(f"🎯 ALPHACATCH | {ticker_symbol} | Z-Score: {calculated_z:+.2f}σ | Level: {trigger_type}")
                send_telegram_alert(
                    ticker=ticker_symbol,
                    trigger_type=trigger_type,
                    score=intensity_score,
                    insider=row['Insider'],
                    position=row['Position'],
                    value=val,
                    z_score=calculated_z
                )
            
    db_connection.commit()
    print(f"\n✅ Synchronization Finished. Committed {new_records_saved} new anomalies.")
else:
    print("[-] No significant tracking entries found in this wire period loop.")

scanned_count = len(recent_filings)
cursor.execute("UPDATE system_telemetry SET metric_value = metric_value + ? WHERE metric_key = 'total_raw_scans'", (scanned_count,))
db_connection.commit()
db_connection.close()
print("Done. Ready for frontend visual display.")