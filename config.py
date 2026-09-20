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

# AI Provider API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
XAI_API_KEY = os.getenv("XAI_API_KEY", "").strip()

DEFAULT_WORKSPACE = os.getenv("DEFAULT_WORKSPACE", str(BASE_DIR / "workspace"))
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash").strip()

def get_api_key_for_provider(provider: str) -> str:
    """Returns the API key configured for a given provider."""
    provider_lower = provider.lower()
    if provider_lower in ("google", "gemini"):
        return os.getenv("GEMINI_API_KEY", GEMINI_API_KEY).strip()
    elif provider_lower in ("openai",):
        return os.getenv("OPENAI_API_KEY", OPENAI_API_KEY).strip()
    elif provider_lower in ("anthropic", "claude"):
        return os.getenv("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY).strip()
    elif provider_lower in ("deepseek",):
        return os.getenv("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY).strip()
    elif provider_lower in ("xai", "grok"):
        return os.getenv("XAI_API_KEY", XAI_API_KEY).strip()
    return ""

def get_configured_providers() -> list[str]:
    """Returns list of providers that have an API key configured."""
    providers = []
    if get_api_key_for_provider("google"):
        providers.append("Google Gemini")
    if get_api_key_for_provider("openai"):
        providers.append("OpenAI")
    if get_api_key_for_provider("anthropic"):
        providers.append("Anthropic")
    if get_api_key_for_provider("deepseek"):
        providers.append("DeepSeek")
    if get_api_key_for_provider("xai"):
        providers.append("xAI")
    return providers

def validate_config():
    """Validates necessary credentials and returns actionable error messages."""
    errors = []
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        errors.append("TELEGRAM_BOT_TOKEN is missing or not set in .env")
    if not TELEGRAM_ALLOWED_USER_ID:
        errors.append("TELEGRAM_ALLOWED_USER_ID is missing or not set in .env")
    
    # Check if at least one AI key is present
    if not get_configured_providers():
        errors.append("No AI Provider API key found in .env (add at least GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, or DEEPSEEK_API_KEY)")
    
    return errors

