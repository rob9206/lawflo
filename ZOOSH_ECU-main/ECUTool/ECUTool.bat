@echo off
:: ECU Communication Tool Launcher

title ECU Tool

cd /d "%~dp0"

echo ========================================
echo    ECU Communication Tool
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found! Please install Python 3.x
    pause
    exit /b 1
)

:: Run GUI
python ecu_gui.py

pause

