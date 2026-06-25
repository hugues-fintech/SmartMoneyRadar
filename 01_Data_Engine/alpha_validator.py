import os
import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime

# 1. PATH SETUP
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if '__file__' in locals() else os.getcwd()
DB_PATH = os.path.join(BASE_DIR, "02_Database", "insider_vault.db")

if not os.path.exists(DB_PATH):
    # Fallback for desktop structures
    DB_PATH = r"C:\Users\Amy\Desktop\SmartMoneyRadar\02_Database\insider_vault.db"

print("==========================================================")
print(" 🔬 SMART MONEY RADAR: ALPHA VALIDATION ENGINE")
print("==========================================================")
print(f"Reading from Archive: {DB_PATH}\n")

# 2. CONNECT AND PULL HISTORIC ENTRIES
try:
    db_connection = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM insider_trades", db_connection)
    db_connection.close()
except Exception as e:
    print(f"❌ Error connecting to database: {e}")
    exit()

if df.empty:
    print("❌ The database archive is empty. Run the insider data engine first to collect records.")
    exit()

print(f"Loaded {len(df)} historic insider tracking blocks. Fetching live performance deltas...")

# 3. PERFORMANCE EVALUATION LOOP
performance_records = []
unique_tickers = df['ticker'].unique()

print(f"Syncing live market data for {len(unique_tickers)} unique symbols via Yahoo Finance...")
live_prices = {}

for ticker in unique_tickers:
    try:
        ticker_obj = yf.Ticker(ticker)
        # Fetching current market price smoothly
        fast_info = ticker_obj.fast_info
        if 'last_price' in fast_info and fast_info['last_price'] is not None:
            live_prices[ticker] = fast_info['last_price']
        else:
            # Fallback method if fast_info is blank
            history = ticker_obj.history(period="1d")
            if not history.empty:
                live_prices[ticker] = history['Close'].iloc[-1]
    except Exception:
        continue

# Calculate deltas
for _, row in df.iterrows():
    ticker = row['ticker']
    insider_price = row['price']
    
    if ticker in live_prices:
        current_price = live_prices[ticker]
        # Calculate percentage return: ((Current - Insider) / Insider) * 100
        return_pct = ((current_price - insider_price) / insider_price) * 100
        
        performance_records.append({
            'ticker': ticker,
            'insider': row['insider_name'],
            'position': row['position'],
            'buy_price': insider_price,
            'current_price': current_price,
            'return_pct': return_pct,
            'value': row['total_value']
        })

if not performance_records:
    print("❌ Could not map live market prices to the archived tickers.")
    exit()

df_perf = pd.DataFrame(performance_records)

# 4. COMPUTE INSTITUTIONAL ALPHA METRICS
winning_trades = df_perf[df_perf['return_pct'] > 0]
win_rate = (len(winning_trades) / len(df_perf)) * 100
avg_return = df_perf['return_pct'].mean()
max_gain = df_perf['return_pct'].max()
total_tracked_value = df_perf['value'].sum()

print("\n==========================================================")
print(" 📊 SYSTEM PERFORMANCE METRICS FOR INVESTORS")
print("==========================================================")
print(f"✅ Total Signals Validated:  {len(df_perf)}")
print(f"🐋 Total Capital Tracked:   ${total_tracked_value:,.2f}")
print(f"🎯 Strategy Win Rate:       {win_rate:.1f}%")
print(f"📈 Average Signal Return:   {avg_return:+.2f}%")
print(f"🚀 Maximum Single Outrun:   {max_gain:+.2f}%")
print("==========================================================")

# Show the top 5 most profitable insider moves currently in your database
print("\n🔥 TOP 5 ACTIVE HIGH-CONVICTION LEADERBOARD:")
df_top = df_perf.sort_values(by='return_pct', ascending=False).head(5)
for idx, row in df_top.iterrows():
    print(f"• {row['ticker']} ({row['position']}): Bought @ ${row['buy_price']:.2f} ➔ Now @ ${row['current_price']:.2f} ({row['return_pct']:+.2f}%)")