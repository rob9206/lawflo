@echo off
setlocal

echo ==========================================
echo   Killing LawFlow backend processes...
echo ==========================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue';$ports=@(5002,5000,8000,8001);$targets=@();if(Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue){foreach($port in $ports){$targets += (Get-NetTCPConnection -State Listen -LocalPort $port | Select-Object -ExpandProperty OwningProcess)}}else{foreach($port in $ports){$targets += (netstat -ano -p tcp | Select-String (':'+$port+'\s+.*LISTENING\s+(\d+)$') | ForEach-Object {([regex]::Match($_.ToString(),'(\d+)$')).Groups[1].Value})}};$procMatches=Get-CimInstance Win32_Process | Where-Object { ($_.Name -in @('python.exe','pythonw.exe','uvicorn.exe','flask.exe')) -and ( ($_.CommandLine -match 'api\.app') -or ($_.CommandLine -match 'LawFlow\\api') -or ($_.CommandLine -match 'uvicorn') -or ($_.CommandLine -match 'flask\s+run') ) };$targets += ($procMatches | Select-Object -ExpandProperty ProcessId);$targets=$targets|Where-Object {$_}|ForEach-Object {[int]$_}|Sort-Object -Unique;if(-not $targets){Write-Host 'No backend processes found.';exit 0};Write-Host 'Found backend processes:';Get-CimInstance Win32_Process | Where-Object {$targets -contains $_.ProcessId} | Select-Object ProcessId,Name,CommandLine | Format-Table -AutoSize;Write-Host '';foreach($p in $targets){try{Stop-Process -Id $p -Force -ErrorAction Stop;Write-Host ('Killed PID '+$p)}catch{Write-Host ('Failed to kill PID '+$p+': '+$_.Exception.Message)}};Start-Sleep -Milliseconds 300;$still=@();if(Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue){foreach($port in $ports){$still += (Get-NetTCPConnection -State Listen -LocalPort $port | Select-Object -ExpandProperty OwningProcess)}}else{foreach($port in $ports){$still += (netstat -ano -p tcp | Select-String (':'+$port+'\s+.*LISTENING\s+(\d+)$') | ForEach-Object {([regex]::Match($_.ToString(),'(\d+)$')).Groups[1].Value})}};$still=$still|Where-Object {$_}|Sort-Object -Unique;Write-Host '';if($still){Write-Host ('Still listening on backend ports (5002/5000/8000/8001): '+($still -join ', '))}else{Write-Host 'Backend ports are now free.'}"

echo.
echo Done.
pause
