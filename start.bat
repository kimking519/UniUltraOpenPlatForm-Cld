@echo off
title UniUltra Open Platform - Launcher
echo ======================================================
echo           Starting UniUltra Open Platform...
echo ======================================================
echo.

:: Set project root to the directory where the script is located
set "PROJECT_ROOT=%~dp0"
:: Remove trailing backslash if any
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

:: Check if directory exists
if not exist "%PROJECT_ROOT%" (
    echo [ERROR] Project directory not found: %PROJECT_ROOT%
    pause
    exit /b
)

:: Change to project directory (absolute path)
cd /d "%PROJECT_ROOT%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to change directory to: %PROJECT_ROOT%
    pause
    exit /b
)

:: Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please ensure Python is in PATH.
    pause
    exit /b
)

:: Try activating virtual environment
set "VENV_PATH="
if exist "%PROJECT_ROOT%\venv\Scripts\activate.bat" (
    set "VENV_PATH=%PROJECT_ROOT%\venv\Scripts\activate.bat"
) else if exist "%PROJECT_ROOT%\.venv\Scripts\activate.bat" (
    set "VENV_PATH=%PROJECT_ROOT%\.venv\Scripts\activate.bat"
)

if defined VENV_PATH (
    echo [INFO] Activating virtual environment...
    call "%VENV_PATH%"
) else (
    echo [WARN] No virtual environment found. Using global Python.
)

:: Run main application
echo [INFO] Opening browser at http://127.0.0.1:8000 ...
start "" "http://127.0.0.1:8000"

echo [INFO] Running main.py...
python "%PROJECT_ROOT%\main.py"

:: Keep window open if crashed
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with code: %errorlevel%
)

pause
