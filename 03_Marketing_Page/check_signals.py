import sqlite3
import os
import subprocess

# 1. SETUP PATHS (Using verified absolute locations)
DB_PATH = r"C:\Users\Amy\Desktop\SmartMoneyRadar\02_Database\insider_vault.db"
HTML_PATH = r"C:\Users\Amy\Desktop\SmartMoneyRadar\4_webupload\index.html"
PROJECT_ROOT = r"C:\Users\Amy\Desktop\SmartMoneyRadar"

# A list of all common locations Git hides on Windows
POSSIBLE_GIT_PATHS = [
    r"C:\Program Files\Git\cmd\git.exe",
    r"C:\Program Files\Git\bin\git.exe",
    r"C:\Program Files (x86)\Git\cmd\git.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app\git\cmd\git.exe")
]

# Resolve GitHub Desktop wildcard path if it exists
import glob
resolved_paths = []
for p in POSSIBLE_GIT_PATHS:
    if "*" in p:
        resolved_paths.extend(glob.glob(p))
    else:
        resolved_paths.append(p)

# Find the first one that actually exists
EXE_CMD = "git"
for path in resolved_paths:
    if os.path.exists(path):
        EXE_CMD = path
        break

print("==========================================================")
print(" 🚀 SMART MONEY RADAR - WEB SYNC BRIDGE ACTIVE")
print("==========================================================")
print(f"🔍 Located Git Executable at: {EXE_CMD}")

try:
    # 2. EXTRACT RECENT TEASER SIGNALS FROM LOCAL DATABASE
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ticker, company, insider_name, position, total_value, filing_date 
        FROM insider_trades 
        ORDER BY filing_date DESC, total_value DESC 
        LIMIT 5
    """)
    recent_trades = cursor.fetchall()
    conn.close()
    
    if not recent_trades:
        print("ℹ️ No historical trades found in your database yet to push to the web.")
        exit()

    print(f"📊 Extracted {len(recent_trades)} recent signals for the public teaser feed.")

    # 3. CONVERT DATABASE ROWS INTO CLEAN HTML SNIPPETS
    html_rows = ""
    for row in recent_trades:
        ticker, company, insider, position, value, date = row
        formatted_value = f"${value:,.2f}"
        
        html_rows += f"""
            <div style="background: rgba(0,0,0,0.02); border: 1px solid #e9ecef; padding: 16px; border-radius: 10px; margin-bottom: 12px; font-family: -apple-system, sans-serif;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #0066cc; font-weight: bold; font-size: 1.05em;">[FLAGGED] {ticker}</span>
                    <span style="color: #02b159; font-weight: bold;">{formatted_value}</span>
                </div>
                <div style="color: #495057; font-size: 0.9em; line-height: 1.4;">
                    <strong>Company:</strong> {company}<br>
                    <strong>Insider:</strong> {insider} ({position})<br>
                    <span style="color: #adb5bd; font-size: 0.85rem;">Logged on: {date}</span>
                </div>
            </div>
        """

    # 4. READ CURRENT INDEX.HTML AND INJECT LIVE FEED
    with open(HTML_PATH, "r", encoding="utf-8") as file:
        html_content = file.read()

    START_MARKER = ""
    END_MARKER = ""

    start_idx = html_content.find(START_MARKER) + len(START_MARKER)
    end_idx = html_content.find(END_MARKER)

    updated_html = html_content[:start_idx] + "\n" + html_rows + "\n" + html_content[end_idx:]

    with open(HTML_PATH, "w", encoding="utf-8") as file:
        file.write(updated_html)
        
    print("📝 Webpage file (index.html) successfully updated with fresh database rows.")

    # 5. EXECUTE HANDS-FREE GIT PUSH (Bypassing shell issues)
    print("\n📦 Initiating automated Git handshake...")
    
    # Passing arguments as a clean array directly to the executable
    subprocess.run([EXE_CMD, "add", "."], cwd=PROJECT_ROOT, check=True)
    subprocess.run([EXE_CMD, "commit", "-m", "Automated Radar Pipeline Sync [Live Feed Update]"], cwd=PROJECT_ROOT, check=True)
    subprocess.run([EXE_CMD, "push", "origin", "main"], cwd=PROJECT_ROOT, check=True)
    
    print("\n🚀 SUCCESS! Live code pushed to GitHub. Vercel is building your updates right now at:")
    print("👉 https://smart-money-radar-beta.vercel.app/")

except Exception as e:
    print(f"❌ Pipeline Sync Error: {e}")