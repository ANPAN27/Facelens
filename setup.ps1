# FaceLens CLI - Windows setup (PowerShell)
# Usage: right-click -> Run with PowerShell, or enter this in a terminal.
Set-Location $PSScriptRoot

Write-Host "============================================"
Write-Host "  FACELENS CLI - Windows Setup (PowerShell)"
Write-Host "============================================"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found. Install Python 3.9+ from https://www.python.org/downloads/"
    pause
    exit 1
}

if (-not (Test-Path venv)) {
    Write-Host "[1/3] Creating virtual environment..."
    python -m venv venv
} else {
    Write-Host "[1/3] Virtual environment already exists."
}

Write-Host "[2/3] Installing dependencies..."
& .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path .env)) {
    Write-Host "[3/3] Creating .env from template..."
    Copy-Item .env.example .env
    Write-Host "NOTE: Open .env and set PRIVATE_KEY and CONTRACT_ADDRESS."
}

Write-Host ""
Write-Host "============================================"
Write-Host "  SETUP COMPLETE"
Write-Host "============================================"
Write-Host ""
Write-Host "Run a search:"
Write-Host "  python main.py search --image C:\path\to\person.jpg"
Write-Host ""
pause