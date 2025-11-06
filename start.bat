@echo off
REM Koatsume - Startup script for Windows
REM This script creates a virtual environment if needed, installs requirements, and runs the app

setlocal

cd /d "%~dp0"

echo.
echo 🌟 Koatsume Startup Script
echo ==========================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed or not in PATH.
    echo Please install Python 3.7 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo ✓ Python found
python --version

REM Create virtual environment if it doesn't exist
if not exist "venv\" (
    echo.
    echo 📦 Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Error: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo ✓ Virtual environment created
) else (
    echo ✓ Virtual environment already exists
)

REM Activate virtual environment
echo.
echo 🔌 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️  Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

REM Install requirements
echo 📥 Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Error: Failed to install requirements
    pause
    exit /b 1
)

echo ✓ Requirements installed
echo.
echo 🚀 Starting Koatsume...
echo.

REM Run the application
python app.py

pause
