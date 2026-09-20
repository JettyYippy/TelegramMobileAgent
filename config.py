import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_ALLOWED_USER_ID_STR = os.getenv("TELEGRAM_ALLOWED_USER_ID", "").strip()

try:
    TELEGRAM_ALLOWED_USER_ID = int(TELEGRAM_ALLOWED_USER_ID_STR) if TELEGRAM_ALLOWED_USER_ID_STR else None
except ValueError:
    TELEGRAM_ALLOWED_USER_ID = None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DEFAULT_WORKSPACE = os.getenv("DEFAULT_WORKSPACE", str(BASE_DIR / "workspace"))
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash").strip()

def validate_config():
    """Validates necessary credentials and returns actionable error messages."""
    errors = []
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        errors.append("TELEGRAM_BOT_TOKEN is missing or not set in .env")
    if not TELEGRAM_ALLOWED_USER_ID:
        errors.append("TELEGRAM_ALLOWED_USER_ID is missing or not set in .env")
    
    return errors
