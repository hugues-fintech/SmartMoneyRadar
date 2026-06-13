import time
import subprocess
import sys
from datetime import datetime

# Set frequency interval (900 seconds = 15 minutes)
INTERVAL_SECONDS = 900

print("==========================================================")
print(" ⏰ AUTOMATED INSIDER BACKGROUND WORKER ACTIVE")
print("==========================================================")
print(f"System will execute a live SEC scan every {INTERVAL_SECONDS // 60} minutes.")
print("Leave this window running in the background at your desk.\n")

try:
    while True:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"🔄 [{current_time}] Initiating scheduled SEC pipeline scan...")
        
        # This executes your database script cleanly from inside the loop
        # We pass an empty input back to prevent the inner script's 'input()' block from pausing the loop
        process = subprocess.Popen(
            [sys.executable, "automated_insider_engine.py"],
            stdin=subprocess.PIPE,
            text=True
        )
        
        # Wait for the database engine to finish processing the 100 packets
        process.communicate(input="\n")
        
        print(f"\n💤 Scan cycle complete. Next pipeline execution in {INTERVAL_SECONDS // 60} minutes.")
        print("Press CTRL+C at any time in this terminal to stop the automation.")
        print("-" * 70)
        
        # Clean countdown timer display inside the terminal loop
        for remaining in range(INTERVAL_SECONDS, 0, -1):
            mins, secs = divmod(remaining, 60)
            sys.stdout.write(f"\r⏳ Next scan in: {mins:02d}:{secs:02d} ... ")
            sys.stdout.flush()
            time.sleep(1)
            
        print("\n")

except KeyboardInterrupt:
    print("\n\n🛑 Automation worker shut down safely by user.")