Set-Location $PSScriptRoot
Write-Host "Starting TelegramMobileAgent..." -ForegroundColor Cyan

if (-not (Test-Path ".\.venv")) {
    Write-Host "Creating virtual environment .venv..." -ForegroundColor Yellow
    python -m venv .venv
    & ".\.venv\Scripts\pip.exe" install -r requirements.txt
}

& ".\.venv\Scripts\python.exe" bot.py
