@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "ROOT=%CD%"
set "PACKAGE_ROOT=%TEMP%\LawFlowShare_%RANDOM%"
set "STAGING=%PACKAGE_ROOT%\LawFlow"
set "ZIP_PATH=%USERPROFILE%\Desktop\LawFlow.zip"

echo [1/4] Creating staging folder...
if exist "%PACKAGE_ROOT%" rmdir /s /q "%PACKAGE_ROOT%"
mkdir "%STAGING%" >nul 2>&1
if errorlevel 1 goto STAGING_FAIL

echo [2/4] Copying project files (excluding dev/runtime artifacts)...
robocopy "%ROOT%" "%STAGING%" /E /R:1 /W:1 ^
  /XD ".git" ".venv" "venv" ".cursor" "data" "dist" "build" "installer\output" "frontend\node_modules" "frontend\dist" "__pycache__" ^
  /XF ".env" "*.pyc" "*.pyo" "Thumbs.db" ".DS_Store" >nul
set "ROBO_EXIT=%ERRORLEVEL%"
if %ROBO_EXIT% GEQ 8 goto COPY_FAIL

echo [3/4] Building zip on Desktop...
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path '%ZIP_PATH%') { Remove-Item '%ZIP_PATH%' -Force }; Compress-Archive -Path '%STAGING%' -DestinationPath '%ZIP_PATH%' -Force"
if errorlevel 1 goto ZIP_FAIL

echo [4/4] Cleaning up temporary files...
rmdir /s /q "%PACKAGE_ROOT%" >nul 2>&1

echo.
echo Done. Share this file with your friend:
echo   %ZIP_PATH%
echo.
pause
goto END

:STAGING_FAIL
echo [ERROR] Failed to create staging folder.
goto FAIL_EXIT

:COPY_FAIL
echo [ERROR] Failed while copying files into staging folder.
goto FAIL_EXIT

:ZIP_FAIL
echo [ERROR] Failed to create LawFlow.zip.
goto FAIL_EXIT

:FAIL_EXIT
if exist "%PACKAGE_ROOT%" rmdir /s /q "%PACKAGE_ROOT%" >nul 2>&1
echo.
pause
exit /b 1

:END
endlocal
