# Run OCR Analysis Tool
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $scriptDir

Write-Host "=== OCR Analysis Tool ===" -ForegroundColor Cyan
Write-Host ""

# Check for virtual env
$venv = Join-Path $scriptDir ".venv"
if (Test-Path (Join-Path $venv "Scripts\Activate.ps1")) {
    Write-Host "Activating virtual environment ..." -ForegroundColor Yellow
    & (Join-Path $venv "Scripts\Activate.ps1")
}

# Check Python
try {
    $py = Get-Command python -ErrorAction Stop
} catch {
    Write-Host "ERROR: Python not found." -ForegroundColor Red
    exit 1
}

Write-Host "Running preprocess.py ..." -ForegroundColor Green
python preprocess.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: preprocess.py exited with code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
