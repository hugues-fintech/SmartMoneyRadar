@echo off
:: Step 1: Change directory to your exact project root folder
cd /d "C:\Users\Amy\Desktop\SmartMoneyRadar"

:: Step 2: Run your scraper script using the correct folder path syntax
python "01_Data_Engine\automated_insider_engine.py"

:: Step 3: Keep the window open if it fails so you can read the error
pause