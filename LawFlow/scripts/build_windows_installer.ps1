$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host "[1/5] Building frontend production assets..."
Set-Location (Join-Path $projectRoot "frontend")
npm install
npm run build
Set-Location $projectRoot

Write-Host "[2/5] Installing/refreshing build tools..."
python -m pip install --upgrade pip
python -m pip install pyinstaller

Write-Host "[3/5] Building LawFlow.exe with PyInstaller..."
python -m PyInstaller `
  --noconfirm `
  --clean `
  --name LawFlow `
  --onefile `
  --add-data "api;api" `
  --add-data "frontend/dist;frontend/dist" `
  --add-data ".env.example;." `
  launcher.py

Write-Host "[4/5] Looking for Inno Setup (ISCC)..."
$isccCandidates = @(
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)

$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
  Write-Warning "Inno Setup not found. Install it, then run:"
  Write-Warning "  ""C:\Program Files (x86)\Inno Setup 6\ISCC.exe"" installer\LawFlow.iss"
  exit 0
}

Write-Host "[5/5] Building LawFlowSetup.exe installer..."
& $iscc (Join-Path $projectRoot "installer\LawFlow.iss")

Write-Host ""
Write-Host "Done. Output files:"
Write-Host "  - dist\LawFlow.exe"
Write-Host "  - installer\output\LawFlowSetup.exe"
