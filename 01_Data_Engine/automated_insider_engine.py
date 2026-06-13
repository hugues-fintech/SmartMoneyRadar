import os
import sqlite3
import pandas as pd
from edgar import set_identity, get_filings

# 1. ESTABLISH SEC IDENTITY
set_identity("Hugues Leccia hugues.leccia@example.com")

# 2. AUTOMATED RELATIVE PATH MAPPING FOR CLOUD COMPATIBILITY
# This finds the root folder dynamically whether on Windows or a Linux cloud server
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "02_Database", "insider_vault.db")

# Ensure the directory exists in the cloud environment
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

db_connection = sqlite3.connect(DB_PATH)
cursor = db_connection.cursor()

# Create the master tracking table
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
    trigger_type TEXT,
    filing_date TEXT
)
""")
db_connection.commit()

print("==========================================================")
print(" 📦 CLOUD-READY INSIDER DATA STORAGE ENGINE ACTIVE")
print("==========================================================")
print(f"Target Database Path: {DB_PATH}")
print("Pulling live tracking buffer from SEC servers...")

# Fetch 100 recent Form 4 filings
filing_buffer = get_filings(form="4").latest(100)
all_purchases = []

print("Scanning documents for open-market cash injections...")

for index, filing in enumerate(filing_buffer, 1):
    try:
        form4_data = filing.obj()
        if form4_data is None:
            continue
            
        df_raw = form4_data.to_dataframe()
        if df_raw.empty:
            continue
            
        # Isolate purchases using our microscopic string rules
        df_buys = df_raw[
            (df_raw['Transaction Type'].str.lower() == 'purchase') | 
            (df_raw['Code'].str.upper() == 'P')
        ].copy()
        
        if df_buys.empty:
            continue
            
        # Clean data formats
        df_buys['Shares'] = pd.to_numeric(df_buys['Shares'], errors='coerce')
        df_buys['Price'] = pd.to_numeric(df_buys['Price'], errors='coerce')
        df_buys['Value'] = pd.to_numeric(df_buys['Value'], errors='coerce')
        
        # Unique fingerprint for this specific filing row to prevent duplication
        accession_num = filing.accession_number if hasattr(filing, 'accession_number') else str(filing.url)
        
        for i, row in df_buys.iterrows():
            if row['Shares'] > 0 and row['Price'] > 0:
                calc_val = row['Value'] if row['Value'] > 0 else (row['Shares'] * row['Price'])
                unique_row_id = f"{accession_num}_{i}"
                
                # --- STRIP WHITESPACE & UPPERCASE FOR PERFECT STREAMLIT BADGING MATCHES ---
                clean_position = str(row.get('Position', 'Not Stated')).strip().upper()
                
                all_purchases.append({
                    'filing_id': unique_row_id,
                    'Ticker': row.get('Ticker', filing.ticker if hasattr(filing, 'ticker') else 'UNKNOWN'),
                    'Company': row.get('Issuer', filing.company),
                    'Insider': row.get('Insider', 'Unknown Executive'),
                    'Position': clean_position,
                    'Shares': int(row['Shares']),
                    'Price': float(row['Price']),
                    'Value': float(calc_val),
                    'Date': str(filing.filing_date)
                })
    except Exception:
        continue

# 3. APPLY ALARM LOGIC AND COMMIT TO PERMANENT DATABASE
if not all_purchases:
    print("\nNo valid cash purchases found in this snapshot.")
else:
    df_master = pd.DataFrame(all_purchases)
    
    # Group data to compute trade aggregates
    cluster_summary = df_master.groupby(['Ticker', 'Company']).agg(
        Total_Trades=('Shares', 'count'),
        Total_Capital=('Value', 'sum')
    ).reset_index()
    
    # Filter for companies triggering either our CLUSTER or WHALE criteria
    triggered_companies = cluster_summary[
        (cluster_summary['Total_Trades'] >= 2) | 
        (cluster_summary['Total_Capital'] >= 100000)
    ]
    
    valid_tickers = triggered_companies['Ticker'].tolist()
    df_signals = df_master[df_master['Ticker'].isin(valid_tickers)]
    
    new_records_saved = 0
    
    for _, row in df_signals.iterrows():
        ticker_summary = triggered_companies[triggered_companies['Ticker'] == row['Ticker']].iloc[0]
        reasons = []
        if ticker_summary['Total_Trades'] >= 2: reasons.append("CLUSTER")
        if ticker_summary['Total_Capital'] >= 100000: reasons.append("WHALE")
        trigger_label = " + ".join(reasons)
        
        try:
            # INSERT OR IGNORE avoids duplicates
            cursor.execute("""
            INSERT OR IGNORE INTO insider_trades 
            (filing_id, ticker, company, insider_name, position, shares, price, total_value, trigger_type, filing_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['filing_id'], row['Ticker'], row['Company'], row['Insider'], 
                row['Position'], row['Shares'], row['Price'], row['Value'], 
                trigger_label, row['Date']
            ))
            if cursor.rowcount > 0:
                new_records_saved += 1
        except Exception as e:
            print(f"Database error writing row: {e}")
            
    db_connection.commit()
    print(f"\n✅ Scan complete. Saved {new_records_saved} BRAND NEW signals to your permanent database.")

# Print current total volume in database file
cursor.execute("SELECT COUNT(*) FROM insider_trades")
total_rows = cursor.fetchone()[0]
print(f"📊 Your archive currently holds {total_rows} historic insider entries.")

db_connection.close()