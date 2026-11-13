"""Loads GEMINI_API_KEY and GEMINI_MODEL from the .env file next to this script."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).parent
ENV_FILE = PROJECT_DIR / ".env"
DEFAULT_MODEL = "gemini-3.1-flash-lite"
PLACEHOLDER = "your_api_key_here"


class ConfigError(Exception):
    pass


def load_config() -> tuple[str, str]:
    """Return (api_key, model). Raises ConfigError with a fix-it message."""
    if os.getenv("MOCK_LLM") == "1":
        return "", os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

    if not ENV_FILE.exists():
        raise ConfigError(
            f"Missing {ENV_FILE.name}. Copy .env.example to .env, paste your "
            "Google AI Studio API key, save, and restart the app."
        )
    load_dotenv(dotenv_path=ENV_FILE, override=True)

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    if not api_key or api_key == PLACEHOLDER:
        raise ConfigError(
            "GEMINI_API_KEY is missing. Edit .env, paste your Google AI Studio key "
            "and restart the app."
        )
    return api_key, model
