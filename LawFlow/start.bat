@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title LawFlow Setup
color 0A

set "PYTHON_WINGET_ID=Python.Python.3.12"
set "NODE_WINGET_ID=OpenJS.NodeJS.LTS"

echo.
echo  ==========================================
echo    LawFlow - One-Click Startup
echo  ==========================================
echo.

call :ENSURE_TOOL python "%PYTHON_WINGET_ID%" "Python 3"
if errorlevel 1 goto END

call :ENSURE_TOOL node "%NODE_WINGET_ID%" "Node.js LTS"
if errorlevel 1 goto END

call :ENSURE_ENV_FILE
if errorlevel 1 goto END

call :ENSURE_API_KEY
if errorlevel 1 goto END

if not exist "venv\Scripts\python.exe" (
  echo [SETUP] Creating Python virtual environment...
  python -m venv venv
  if errorlevel 1 goto VENV_FAIL
)

echo [SETUP] Installing Python dependencies...
"venv\Scripts\pip.exe" install -r requirements.txt -q --disable-pip-version-check
if errorlevel 1 goto PIP_FAIL

if not exist "data\uploads" md "data\uploads"
if not exist "data\processed" md "data\processed"

if not exist "frontend\node_modules" (
  echo [SETUP] Installing frontend dependencies (this may take a minute)...
  pushd "frontend"
  npm install
  if errorlevel 1 goto NPM_FAIL
  popd
)

echo [START] Launching backend on http://127.0.0.1:5002 ...
start "LawFlow Backend" cmd /k "cd /d %~dp0 && title LawFlow Backend && venv\Scripts\python.exe api\app.py"

echo [START] Launching frontend on http://localhost:5173 ...
start "LawFlow Frontend" cmd /k "cd /d %~dp0\frontend && title LawFlow Frontend && npm run dev"

echo.
echo  ==========================================
echo    LawFlow is starting!
echo    Opening http://localhost:5173 in 5s...
echo  ==========================================
echo.
ping -n 6 127.0.0.1 >nul
start http://localhost:5173
goto END

:ENSURE_TOOL
set "TOOL_CMD=%~1"
set "WINGET_ID=%~2"
set "TOOL_NAME=%~3"

where "%TOOL_CMD%" >nul 2>&1
if %errorlevel% equ 0 goto :EOF

echo [SETUP] %TOOL_NAME% not found. Attempting auto-install via winget...
where winget >nul 2>&1
if %errorlevel% neq 0 goto NO_WINGET

winget install -e --id %WINGET_ID% --accept-source-agreements --accept-package-agreements
if errorlevel 1 goto INSTALL_FAIL

call :REFRESH_PATH
where "%TOOL_CMD%" >nul 2>&1
if %errorlevel% neq 0 goto INSTALL_FAIL
goto :EOF

:REFRESH_PATH
for /f "delims=" %%P in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')"') do (
  set "PATH=%%P"
)
goto :EOF

:ENSURE_ENV_FILE
if exist ".env" goto :EOF
echo [SETUP] Creating .env from template...
if exist ".env.example" (
  copy ".env.example" ".env" >nul
) else (
  echo ANTHROPIC_API_KEY=sk-ant-your-key-here>.env
)
if not exist ".env" goto ENV_FAIL
goto :EOF

:ENSURE_API_KEY
set "CURRENT_KEY="
for /f "tokens=1,* delims==" %%A in ('findstr /B /I "ANTHROPIC_API_KEY=" ".env"') do (
  set "CURRENT_KEY=%%B"
)

if not defined CURRENT_KEY goto PROMPT_API_KEY
if /I "%CURRENT_KEY%"=="sk-ant-your-key-here" goto PROMPT_API_KEY
goto :EOF

:PROMPT_API_KEY
echo [SETUP] Prompting for Anthropic API key...
set "INPUT_KEY="
for /f "usebackq delims=" %%K in (`powershell -NoProfile -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; $k=[Microsoft.VisualBasic.Interaction]::InputBox('Enter your Anthropic API key (starts with sk-ant-):','LawFlow setup',''); Write-Output $k"`) do (
  set "INPUT_KEY=%%K"
)

if not defined INPUT_KEY (
  echo [ERROR] Anthropic API key is required.
  goto API_KEY_FAIL
)

powershell -NoProfile -Command "$envFile = Join-Path (Get-Location) '.env'; $newKey = '%INPUT_KEY%'; $lines = @(); if (Test-Path $envFile) { $lines = Get-Content $envFile }; if (($lines | Select-String '^ANTHROPIC_API_KEY=' -Quiet)) { $lines = $lines | ForEach-Object { if ($_ -match '^ANTHROPIC_API_KEY=') { 'ANTHROPIC_API_KEY=' + $newKey } else { $_ } } } else { $lines += 'ANTHROPIC_API_KEY=' + $newKey }; Set-Content -Path $envFile -Value $lines -Encoding UTF8"
if errorlevel 1 goto API_KEY_FAIL
goto :EOF

:NO_WINGET
echo.
echo [ERROR] winget is not available, so %TOOL_NAME% could not be auto-installed.
echo Install required tools, then re-run start.bat:
echo   Python 3.8+: https://www.python.org/downloads/
echo   Node.js 18+: https://nodejs.org/
echo.
pause
exit /b 1

:INSTALL_FAIL
echo.
echo [ERROR] Failed to auto-install %TOOL_NAME%.
echo Please install it manually, then re-run start.bat.
echo.
pause
exit /b 1

:ENV_FAIL
echo [ERROR] Failed to create .env file.
pause
exit /b 1

:API_KEY_FAIL
echo.
echo [ERROR] Could not save Anthropic API key.
echo You can manually edit .env and set ANTHROPIC_API_KEY=your-key.
echo.
pause
exit /b 1

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
endlocal
