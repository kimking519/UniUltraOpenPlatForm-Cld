@echo off
title UniUltra Open Platform - Restarting
echo ======================================================
echo           Restarting UniUltra Open Platform...
echo ======================================================

echo [INFO] Stopping existing python main.py processes...
:: /fi "IMAGENAME eq python.exe" filters for Python processes
:: /fi "WINDOWTITLE eq UniUltra Open Platform - Launcher" or similar could be used,
:: but killing main.py directly via WMIC is more reliable if it was started in background.
wmic process where "name='python.exe' and commandline like '%%main.py%%'" delete >nul 2>&1

echo [INFO] Wait a moment for processes to exit...
timeout /t 2 /nobreak >nul

:: Set project root to absolute path
set "PROJECT_ROOT=%~dp0"
:: Remove trailing backslash if any
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

cd /d "%PROJECT_ROOT%"

echo [INFO] Starting application...
:: Use start to launch it in a new window with a clear title
start "UniUltra Open Platform" cmd /c "%PROJECT_ROOT%\start.bat"

echo [SUCCESS] Restart command issued!
timeout /t 3
exit
