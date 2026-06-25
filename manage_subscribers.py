import sqlite3
import re
from datetime import datetime
import os

# Strict regex pattern to validate genuine email structures
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

def init_subscriber_table(db_path):
    """Creates the CRM subscriber table if it doesn't exist yet."""
    # Ensure the directory path exists before trying to connect
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("[*] Checking subscriber table infrastructure...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS beta_subscribers (
            email TEXT PRIMARY KEY,
            signup_date TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            source TEXT DEFAULT 'terminal_landing',
            last_active_date TEXT,
            email_count INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()
    print("[+] Subscriber table is fully initialized and ready.")

def add_new_subscriber(email, source="terminal_landing", db_path="02_Database/insider_vault.db"):
    """Sanitizes, validates, and saves a subscriber to the database."""
    # Clean the input (lowercase, remove spaces)
    clean_email = email.strip().lower() if email else ""
    
    # Validate the format
    if not bool(re.match(EMAIL_REGEX, clean_email)):
        print(f"[X] Rejected: '{email}' is not a valid email address.")
        return False
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        cursor.execute("""
            INSERT INTO beta_subscribers (email, signup_date, status, source, last_active_date)
            VALUES (?, ?, 'active', ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                status = 'active',
                last_active_date = excluded.last_active_date;
        """, (clean_email, current_timestamp, source, current_timestamp))
        
        conn.commit()
        print(f"[+] Success! Indexed subscriber: {clean_email}")
        return True
    except sqlite3.Error as e:
        print(f"[X] Database error: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    # Define our standard database path
    TARGET_DB = "02_Database/insider_vault.db"
    
    # 1. Initialize the table
    init_subscriber_table(TARGET_DB)
    
    # 2. Run a quick test entry to verify it works
    print("\n[*] Running ingestion pipeline test...")
    add_new_subscriber("test_user@smartmoneyradar.com", source="terminal_landing", db_path=TARGET_DB)