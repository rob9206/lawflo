@echo off
setlocal EnableExtensions EnableDelayedExpansion
echo Starting LawFlow Backend and Frontend...
echo.

call :CHECK_FRONTEND_PORT
if errorlevel 1 goto PORT_IN_USE

REM Start Flask backend in a new window
echo Starting Flask backend...
start "LawFlow Backend" cmd /k "cd /d %~dp0 && python -m api.app"

REM Wait a moment for backend to start
timeout /t 2 /nobreak >nul

REM Start Vite frontend in a new window
echo Starting Vite frontend...
start "LawFlow Frontend" cmd /k "cd /d %~dp0frontend && npm run dev -- --strictPort"

echo Waiting for frontend to become reachable on http://localhost:5173 ...
call :WAIT_FOR_FRONTEND
if errorlevel 1 goto FRONTEND_NOT_READY
start "" http://localhost:5173

echo.
echo Both services are starting in separate windows.
echo Backend: http://localhost:5002
echo Frontend: http://localhost:5173 (strict port mode)
echo.
echo Press any key to exit this window (services will continue running)...
pause >nul
goto END

:CHECK_FRONTEND_PORT
set "FRONTEND_PORT_PID="
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$portPid = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue ^| Select-Object -First 1 -ExpandProperty OwningProcess; if ($portPid) { Write-Output $portPid }"`) do (
  set "FRONTEND_PORT_PID=%%P"
)
if defined FRONTEND_PORT_PID (
  exit /b 1
)
exit /b 0

:WAIT_FOR_FRONTEND
set "FRONTEND_READY="
for /L %%I in (1,1,30) do (
  powershell -NoProfile -Command "try { $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:5173' -UseBasicParsing -TimeoutSec 2; if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) { exit 0 } else { exit 1 } } catch { exit 1 }"
  if !errorlevel! equ 0 (
    set "FRONTEND_READY=1"
    goto :EOF
  )
  timeout /t 1 /nobreak >nul
)
if not defined FRONTEND_READY exit /b 1
exit /b 0

:PORT_IN_USE
echo.
echo [ERROR] Port 5173 is already in use.
echo [ERROR] Close the existing process and run run.bat again.
echo [HINT] netstat -ano ^| findstr :5173
echo.
pause >nul
goto END

:FRONTEND_NOT_READY
echo.
echo [ERROR] Frontend did not become reachable on http://localhost:5173.
echo [ERROR] Check the "LawFlow Frontend" window for errors.
echo.
pause >nul

:END
endlocal