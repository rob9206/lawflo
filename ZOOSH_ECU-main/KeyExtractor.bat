@echo off
:: Dynojet Key Extractor GUI Launcher
:: Double-click to open the graphical interface

title Dynojet Key Extractor

:: Change to script directory
cd /d "%~dp0"

:: Run the GUI (pythonw for no console window)
start "" pythonw "%~dp0KeyExtractorGUI.pyw"

:: If pythonw fails, try python
if %errorlevel% neq 0 (
    python "%~dp0KeyExtractorGUI.pyw"
)

