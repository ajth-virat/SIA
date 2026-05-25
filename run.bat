@echo off
cd /d "%~dp0"
set PYTHON=C:\Users\Admin\AppData\Local\Programs\Python\Python314\python.exe
title Satellite Image Analysis
color 0A

echo.
echo ============================================================
echo   SATELLITE IMAGE ANALYSIS — ONE-CLICK SETUP AND RUN
echo ============================================================
echo.

REM ── CHECK PYTHON ────────────────────────────────────────────
"%PYTHON%" --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found at expected location.
    echo  Expected: %PYTHON%
    pause
    exit /b 1
)
echo  [OK] Python found.

REM ── CREATE VIRTUAL ENVIRONMENT ──────────────────────────────
if not exist venv (
    echo  Setting up environment for the first time...
    "%PYTHON%" -m venv venv
    if errorlevel 1 (
        echo  ERROR: Could not create virtual environment.
        pause
        exit /b 1
    )
    echo  [OK] Environment created.
) else (
    echo  [OK] Environment already exists, skipping setup.
)

REM ── ACTIVATE ────────────────────────────────────────────────
call venv\Scripts\activate.bat

REM ── INSTALL DEPENDENCIES (only on first run) ────────────────
if not exist venv\setup_done.txt (
    echo.
    echo  Installing required packages — this only happens once.
    echo  Please wait, it may take 2-5 minutes...
    echo.
    venv\Scripts\pip.exe install rasterio numpy matplotlib folium geopandas scipy tqdm planetary-computer pystac-client
    if errorlevel 1 (
        echo.
        echo  ERROR: Installation failed. Check your internet connection and try again.
        pause
        exit /b 1
    )
    echo done > venv\setup_done.txt
    echo  [OK] All packages installed.
) else (
    echo  [OK] Packages already installed.
)

REM ── RUN ─────────────────────────────────────────────────────
echo.
echo  Starting analysis...
echo.
venv\Scripts\python.exe fetch_and_run.py
echo.
echo  Script finished. See any errors above.
pause