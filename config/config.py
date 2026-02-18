import json
import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")

_PRICES_PATH = Path(__file__).parent / "models_price.json"


def get_model_prices() -> dict:
    """Load and return the full model price table from models_price.json."""
    if not _PRICES_PATH.exists():
        raise FileNotFoundError(
            f"models_price.json not found at {_PRICES_PATH}. "
            "Create it or copy from config/models_price.json."
        )
    with open(_PRICES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_budget() -> float:
    """Return BUDGET_PER_CALL from .env as a float. Defaults to 1.0."""
    raw = os.getenv("BUDGET_PER_CALL", "1.0")
    try:
        return float(raw)
    except ValueError:
        raise ValueError(
            f"BUDGET_PER_CALL in .env must be a number, got: {raw!r}"
        )


def get_api_key(provider: str) -> str:
    """
    Return the API key for a provider.
    provider must be 'openai' or 'claude'.
    """
    mapping = {
        "openai": "OPENAI_API_KEY",
        "claude": "CLAUDE_API_KEY",
    }
    env_var = mapping.get(provider.lower())
    if env_var is None:
        raise KeyError(f"Unknown provider {provider!r}. Use 'openai' or 'claude'.")
    key = os.getenv(env_var)
    if not key:
        raise KeyError(
            f"{env_var} is not set. Add it to your .env file."
        )
    return key


if __name__ == "__main__":
    prices = get_model_prices()
    print("Loaded models:", list(prices.keys()))
    print("Budget:", get_budget())
