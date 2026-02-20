@echo off
echo Starting LawFlow Backend and Frontend...
echo.

REM Start Flask backend in a new window
echo Starting Flask backend...
start "LawFlow Backend" cmd /k "cd /d %~dp0 && python -m api.app"

REM Wait a moment for backend to start
timeout /t 2 /nobreak >nul

REM Start Vite frontend in a new window
echo Starting Vite frontend...
start "LawFlow Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Both services are starting in separate windows.
echo Backend: http://localhost:5002
echo Frontend: http://localhost:5173
echo.
echo Press any key to exit this window (services will continue running)...
pause >nul
