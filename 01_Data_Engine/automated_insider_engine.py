import os
import sqlite3
import pandas as pd
import yfinance as yf
from edgar import set_identity, get_filings

# 1. ESTABLISH SEC IDENTITY
set_identity("Hugues Leccia h.leccia@gmail.com")

# 2. AUTOMATED RELATIVE PATH MAPPING FOR CLOUD COMPATIBILITY
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "02_Database", "insider_vault.db")

# Ensure the directory exists across environments
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Connect to database and establish connection structure
db_connection = sqlite3.connect(DB_PATH)
cursor = db_connection.cursor()

# Create the master tracking table with clean institutional constraints
cursor.execute("""
CREATE TABLE IF NOT EXISTS insider_trades (
    filing_id TEXT PRIMARY KEY,
    ticker TEXT,
    company TEXT,
    insider_name TEXT,
    position TEXT,
    shares INTEGER,
    price REAL,
    total_value REAL,
    market_cap TEXT,
    avg_volume INTEGER,
    intensity_score REAL,
    trigger_type TEXT,
    filing_date TEXT
)
""")
db_connection.commit()

print("==========================================================")
print(" 📦 INSTITUTIONAL INSIDER DATA STORAGE ENGINE ACTIVE")
print("==========================================================")
print(f"Target Database Path: {DB_PATH}")
print("Pulling live active buffer from SEC servers...")

# Helper function to dynamically pull market sizing framework
def fetch_ticker_market_context(ticker):
    """Fetches market cap and liquidity profiles using yfinance API."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        mcap = info.get('marketCap') or stock.fast_info.get('market_cap')
        vol = info.get('averageVolume') or info.get('volume24hr')
        return (mcap if mcap and mcap > 0 else None, vol if vol and vol > 0 else None)
    except Exception:
        return None, None

# Fetch the active Form 4 filings buffer from EDGAR
try:
    filing_buffer = get_filings(form="4")
    recent_filings = filing_buffer.latest(200) 
    all_purchases = []
    print(f"Successfully connected to SEC. Scanning latest {len(recent_filings)} filings for open-market activity...")
except Exception as e:
    print(f"❌ Critical Error connecting to SEC EDGAR API: {e}")
    recent_filings = []

for index, filing in enumerate(recent_filings, 1):
    try:
        form4_data = filing.obj()
        if form4_data is None:
            continue
            
        df_raw = form4_data.to_dataframe()
        if df_raw.empty:
            continue
            
        # Isolate open-market cash purchases strictly (Code P)
        df_buys = df_raw[
            (df_raw['Transaction Type'].str.lower() == 'purchase') | 
            (df_raw['Code'].str.upper() == 'P')
        ].copy()
        
        if df_buys.empty:
            continue
            
        # Clean and safely cast data formats
        df_buys['Shares'] = pd.to_numeric(df_buys['Shares'], errors='coerce')
        df_buys['Price'] = pd.to_numeric(df_buys['Price'], errors='coerce')
        df_buys['Value'] = pd.to_numeric(df_buys['Value'], errors='coerce')
        
        accession_num = filing.accession_number if hasattr(filing, 'accession_number') else str(filing.url)
        
        for i, row in df_buys.iterrows():
            if row['Shares'] > 0 and row['Price'] > 0:
                calc_val = row['Value'] if row['Value'] > 0 else (row['Shares'] * row['Price'])
                unique_row_id = f"{accession_num}_{i}"
                
                clean_position = str(row.get('Position', 'Not Stated')).strip().upper()
                ticker_symbol = str(row.get('Ticker', filing.ticker if hasattr(filing, 'ticker') else 'UNKNOWN')).strip().upper()
                
                all_purchases.append({
                    'filing_id': unique_row_id,
                    'Ticker': ticker_symbol,
                    'Company': row.get('Issuer', filing.company),
                    'Insider': row.get('Insider', 'Unknown Executive'),
                    'Position': clean_position,
                    'Shares': int(row['Shares']),
                    'Price': float(row['Price']),
                    'Value': float(calc_val),
                    'Date': str(filing.filing_date)
                })
    except Exception as parse_error:
        print(f"⚠️ Skipping filing index {index}: Parsing variance encountered ({parse_error})")
        continue

# 3. APPLY SMART INSIDER METRICS AND COMMIT TO ARCHIVE
if not all_purchases:
    print("\nNo valid open-market cash purchases found in this live snapshot cycle.")
else:
    df_master = pd.DataFrame(all_purchases)
    
    # Extract unique tickers to minimize network calls via yfinance
    unique_tickers = df_master['Ticker'].unique()
    market_context_cache = {}
    
    print(f"[*] Profiling company sizes across {len(unique_tickers)} unique symbols...")
    for t in unique_tickers:
        mcap, av_vol = fetch_ticker_market_context(t)
        market_context_cache[t] = {'mcap': mcap, 'volume': av_vol}
    
    # Calculate historical cluster baseline using existing database entries + current batch
    new_records_saved = 0
    
    for _, row in df_master.iterrows():
        ticker = row['Ticker']
        val = row['Value']
        pos = row['Position']
        f_date = row['Date']
        
        # Pull profile info from context cache
        t_context = market_context_cache.get(ticker, {'mcap': None, 'volume': None})
        mcap = t_context['mcap']
        avg_vol = t_context['volume']
        
        # Calculate dynamic Intensity Score
        intensity_score = 0.0
        if mcap and mcap > 0:
            intensity_score = (val / mcap) * 1000000
            # Executive weight premium (C-Suite Execution Boost)
            if any(title in pos for title in ["CEO", "CFO", "CHIEF EXECUTIVE", "PRESIDENT"]):
                intensity_score *= 1.25
        
        # Evaluate 14-day rolling cluster capacity via historical DB logs
        try:
            cursor.execute("""
                SELECT COUNT(DISTINCT insider_name) FROM insider_trades 
                WHERE ticker = ? AND ABS(strftime('%s', filing_date) - strftime('%s', ?)) <= (14 * 86400)
            """, (ticker, f_date))
            historical_insider_count = cursor.fetchone()[0]
        except Exception:
            historical_insider_count = 0
            
        # Determine internal active cluster count in current live batch
        current_batch_insiders = df_master[df_master['Ticker'] == ticker]['Insider'].nunique()
        total_effective_insiders = max(historical_insider_count, current_batch_insiders)
        
        # Establish high-conviction trigger tags based on institutional rules
        reasons = []
        if total_effective_insiders >= 2:
            reasons.append("CLUSTER")
        if intensity_score >= 1.5 or val >= 250000: # Captures micro-cap intensity OR raw absolute whales
            reasons.append("WHALE")
            
        trigger_label = " + ".join(reasons) if reasons else "STANDARD_SIGNAL"
        
        # Format display metrics
        mcap_display = f"${mcap:,.0f}" if mcap else "Data Unavailable"
        
        try:
            cursor.execute("""
            INSERT OR IGNORE INTO insider_trades 
            (filing_id, ticker, company, insider_name, position, shares, price, total_value, market_cap, avg_volume, intensity_score, trigger_type, filing_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['filing_id'], ticker, row['Company'], row['Insider'], 
                pos, row['Shares'], row['Price'], val, 
                mcap_display, avg_vol, round(intensity_score, 4), trigger_label, f_date
            ))
            if cursor.rowcount > 0:
                new_records_saved += 1
        except Exception as db_error:
            print(f"❌ Database error writing row {row['filing_id']}: {db_error}")
            
    db_connection.commit()
    print(f"\n✅ Scan complete. Saved {new_records_saved} BRAND NEW weighted signals to archive.")

# Output verified state metrics
cursor.execute("SELECT COUNT(*) FROM insider_trades")
total_rows = cursor.fetchone()[0]
print(f"📊 Your verified archive currently holds {total_rows} institutional insider data blocks.")

db_connection.close()