@echo off
cd /d %~dp0
title LawFlow Setup
color 0A

echo.
echo  ==========================================
echo    LawFlow - Starting up...
echo  ==========================================
echo.

:: ---- Check Python ----
python --version >nul 2>&1
if %errorlevel% neq 0 goto NO_PYTHON

:: ---- Check Node ----
node --version >nul 2>&1
if %errorlevel% neq 0 goto NO_NODE

:: ---- Create .env if missing ----
if not exist .env goto MAKE_ENV

:: ---- Check API key is still placeholder ----
findstr /C:"sk-ant-your-key-here" .env >nul 2>&1
if %errorlevel% equ 0 goto NEEDS_KEY

:: ---- Create Python virtual environment ----
if not exist venv\Scripts\python.exe goto MAKE_VENV
goto VENV_DONE

:MAKE_VENV
echo [SETUP] Creating Python virtual environment...
python -m venv venv
if %errorlevel% neq 0 goto VENV_FAIL

:VENV_DONE

:: ---- Install Python deps ----
echo [SETUP] Installing Python dependencies...
venv\Scripts\pip.exe install -r requirements.txt -q --disable-pip-version-check
if %errorlevel% neq 0 goto PIP_FAIL

:: ---- Create data directories ----
if not exist data\uploads md data\uploads
if not exist data\processed md data\processed

:: ---- Install frontend deps ----
if exist frontend\node_modules goto FRONTEND_DONE
echo [SETUP] Installing frontend dependencies (this may take a minute)...
pushd frontend
npm install
if %errorlevel% neq 0 goto NPM_FAIL
popd

:FRONTEND_DONE

:: ---- Start backend ----
echo [START] Launching backend on http://127.0.0.1:5002 ...
start "LawFlow Backend" cmd /k "cd /d %~dp0 && title LawFlow Backend && venv\Scripts\python.exe api\app.py"

:: ---- Start frontend ----
echo [START] Launching frontend on http://localhost:5173 ...
start "LawFlow Frontend" cmd /k "cd /d %~dp0\frontend && title LawFlow Frontend && npm run dev"

:: ---- Open browser ----
echo.
echo  ==========================================
echo    LawFlow is starting!
echo    Opening http://localhost:5173 in 5s...
echo  ==========================================
echo.
ping -n 6 127.0.0.1 >nul
start http://localhost:5173
goto END

:MAKE_ENV
echo [SETUP] Creating .env from template...
copy .env.example .env >nul
goto NEEDS_KEY

:NEEDS_KEY
echo.
echo  !! ACTION REQUIRED !!
echo  Open .env and replace "sk-ant-your-key-here" with your Anthropic API key.
echo  Get a key from: https://console.anthropic.com/
echo.
start notepad .env
pause
goto END

:NO_PYTHON
echo [ERROR] Python not found. Install Python 3.8+ from https://python.org
pause
goto END

:NO_NODE
echo [ERROR] Node.js not found. Install Node.js 18+ from https://nodejs.org
pause
goto END

:VENV_FAIL
echo [ERROR] Failed to create virtual environment.
pause
goto END

:PIP_FAIL
echo [ERROR] Failed to install Python dependencies.
pause
goto END

:NPM_FAIL
echo [ERROR] Failed to install frontend dependencies.
popd
pause
goto END

:END
