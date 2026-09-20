@echo off
cd /d "%~dp0"
echo Starting TelegramMobileAgent...

if not exist .venv (
    echo Virtual environment not found. Creating .venv...
    python -m venv .venv
    .venv\Scripts\pip.exe install -r requirements.txt
)

.venv\Scripts\python.exe bot.py
pause
