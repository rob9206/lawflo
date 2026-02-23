@echo off
:: Dynojet Power Core - Key Extractor Launcher
:: Double-click this file to run the extractor

title Dynojet Key Extractor

echo.
echo ================================================================
echo        DYNOJET POWER CORE - KEY EXTRACTOR
echo ================================================================
echo.

:: Change to script directory
cd /d "%~dp0"

:: Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "%~dp0run_extractor.ps1"

echo.
echo Press any key to exit...
pause > nul

