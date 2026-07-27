@echo off
cd /d "%~dp0"
title Material Property Analyzer

REM ============================================================
REM  Sanity check: make sure the WHOLE folder was downloaded,
REM  not just this run.bat file.
REM ============================================================
if not exist "app.py" (
    echo [ERROR] app.py was not found in this folder.
    echo         You probably downloaded only run.bat.
    echo         Please download the ENTIRE folder ^(app.py, requirements.txt,
    echo         the *.csv.gz data files, the assets folder^) and keep them
    echo         all together, then run run.bat again.
    pause
    exit /b 1
)
if not exist "merged_materials_full.csv.gz" (
    echo [ERROR] Data file "merged_materials_full.csv.gz" is missing.
    echo         Make sure every file in the shared folder was downloaded
    echo         into the same folder as run.bat.
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo         Install it from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

echo [1/3] Checking pip...
python -m pip --version >nul 2>nul
if errorlevel 1 python -m ensurepip --default-pip
python -m pip --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] pip is not available in your Python installation.
    echo         Reinstall Python from python.org ^(keep the "pip" option checked^).
    pause
    exit /b 1
)

echo [2/3] Installing required packages... first run may take a few minutes
python -m pip install -q --no-warn-script-location -r requirements.txt

echo [3/3] Starting the web app. Your browser will open automatically.
python -m streamlit run app.py

pause
