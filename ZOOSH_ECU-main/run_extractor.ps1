<#
.SYNOPSIS
    Dynojet Power Core - Automated Blowfish Key Extractor

.DESCRIPTION
    This script automates the process of extracting Blowfish encryption keys
    from Dynojet Power Core software using Frida.

.USAGE
    .\run_extractor.ps1
    .\run_extractor.ps1 -StartPowerCore
    .\run_extractor.ps1 -OutputFile "keys.txt"
#>

param(
    [switch]$StartPowerCore,
    [string]$OutputFile = "captured_keys.txt",
    [string]$FridaPath = "$env:APPDATA\Python\Python311\Scripts\frida.exe"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HookScript = Join-Path $ScriptDir "extract_key.js"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       DYNOJET POWER CORE - KEY EXTRACTOR LAUNCHER            ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if Frida exists
if (-not (Test-Path $FridaPath)) {
    # Try alternate locations
    $altPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\Scripts\frida.exe",
        "C:\Program Files\Python311\Scripts\frida.exe",
        "C:\Python311\Scripts\frida.exe"
    )
    
    foreach ($path in $altPaths) {
        if (Test-Path $path) {
            $FridaPath = $path
            break
        }
    }
    
    if (-not (Test-Path $FridaPath)) {
        Write-Host "[!] Frida not found. Install it with: pip install frida-tools" -ForegroundColor Red
        exit 1
    }
}

Write-Host "[+] Frida found: $FridaPath" -ForegroundColor Green

# Check if hook script exists
if (-not (Test-Path $HookScript)) {
    Write-Host "[!] Hook script not found: $HookScript" -ForegroundColor Red
    exit 1
}

Write-Host "[+] Hook script: $HookScript" -ForegroundColor Green

# Start Power Core if requested
if ($StartPowerCore) {
    $powerCorePath = "C:\Program Files (x86)\Dynojet Power Core\Power Core.exe"
    if (Test-Path $powerCorePath) {
        Write-Host "[*] Starting Power Core..." -ForegroundColor Yellow
        Start-Process -FilePath $powerCorePath
        Start-Sleep -Seconds 3
    } else {
        Write-Host "[!] Power Core not found at: $powerCorePath" -ForegroundColor Red
    }
}

# Find Power Core process
Write-Host "[*] Looking for Power Core process..." -ForegroundColor Yellow

$maxAttempts = 10
$attempt = 0
$process = $null

while ($attempt -lt $maxAttempts -and -not $process) {
    $process = Get-Process | Where-Object { 
        $_.ProcessName -match "Power.?Core" -or 
        $_.MainWindowTitle -match "Power Core"
    } | Select-Object -First 1
    
    if (-not $process) {
        $attempt++
        Write-Host "    Attempt $attempt/$maxAttempts - Waiting for Power Core..." -ForegroundColor Gray
        Start-Sleep -Seconds 2
    }
}

if (-not $process) {
    Write-Host ""
    Write-Host "[!] Power Core is not running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "    Please start Power Core first, or run:" -ForegroundColor Yellow
    Write-Host "    .\run_extractor.ps1 -StartPowerCore" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "[+] Found Power Core (PID: $($process.Id))" -ForegroundColor Green
Write-Host ""
Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""
Write-Host "[*] Attaching Frida to Power Core..." -ForegroundColor Yellow
Write-Host "[*] Once attached, trigger encryption in Power Core:" -ForegroundColor Yellow
Write-Host "    - Open a .pvv tune file" -ForegroundColor White
Write-Host "    - Connect to a PowerVision device" -ForegroundColor White
Write-Host "    - Access any encrypted content" -ForegroundColor White
Write-Host ""
Write-Host "[*] Press Ctrl+C to stop and save results" -ForegroundColor Yellow
Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor DarkGray
Write-Host ""

# Run Frida
try {
    & $FridaPath -p $process.Id -l $HookScript
} finally {
    Write-Host ""
    Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host "[*] Extraction session ended" -ForegroundColor Yellow
    Write-Host ""
}

