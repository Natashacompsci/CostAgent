import json
import os
from pathlib import Path

from dotenv import load_dotenv

from config.providers import ENV_KEYS, PRESETS

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")

_PRICES_PATH = Path(__file__).parent / "models_price.json"


def _has_valid_key(provider: str) -> bool:
    """Check if a provider has a valid (non-placeholder) API key."""
    env_var = ENV_KEYS.get(provider, "")
    key = os.getenv(env_var, "")
    return bool(key) and not key.startswith("your_")


def _available_providers() -> list[str]:
    """Return list of providers that have valid API keys configured."""
    return [p for p in ENV_KEYS if _has_valid_key(p)]


def _build_mixed_pool() -> dict:
    """Merge models from all available providers, pick best model per level.

    Strategy: for each level (1-3), collect all candidate models across
    providers, then pick the one with the lowest cost_tier (cheapest for L1,
    best value for L2/L3). Ties broken by provider order in PRESETS.
    """
    available = _available_providers()
    candidates: dict[int, list[tuple[str, dict, str]]] = {1: [], 2: [], 3: []}

    for provider in available:
        for model_id, info in PRESETS[provider].items():
            level = info["level"]
            if level in candidates:
                candidates[level].append((model_id, info, provider))

    result = {}
    for level in [1, 2, 3]:
        if not candidates[level]:
            continue
        # L1: pick cheapest (lowest cost_tier)
        # L2: pick mid-range (sort by cost_tier, pick median-ish)
        # L3: pick strongest (highest cost_tier)
        if level == 1:
            best = min(candidates[level], key=lambda x: x[1]["cost_tier"])
        elif level == 3:
            best = max(candidates[level], key=lambda x: x[1]["cost_tier"])
        else:  # level 2
            sorted_candidates = sorted(candidates[level], key=lambda x: x[1]["cost_tier"])
            best = sorted_candidates[len(sorted_candidates) // 2]

        model_id, info, provider = best
        result[model_id] = {**info, "provider": provider}

    return result


def get_active_provider() -> str | None:
    """Return the active provider name, or 'auto' for mixed mode."""
    explicit = os.getenv("PROVIDER", "").strip().lower()
    if explicit:
        if explicit == "auto":
            return "auto"
        if explicit in PRESETS:
            return explicit
        return None

    # Auto-detect: multiple keys → auto mode, single key → that provider
    available = _available_providers()
    if len(available) > 1:
        return "auto"
    if len(available) == 1:
        return available[0]
    return None


def get_model_prices() -> dict:
    """Load model config with priority: PROVIDER env > auto-detect > models_price.json.

    Modes:
      - PROVIDER=google/openai/... → single provider preset
      - PROVIDER=auto → cross-provider mixed routing
      - No PROVIDER + multiple keys → auto mode
      - No PROVIDER + single key → that provider's preset
      - No keys → fallback to models_price.json
    """
    explicit = os.getenv("PROVIDER", "").strip().lower()

    # Explicit single provider
    if explicit and explicit != "auto":
        if explicit not in PRESETS:
            raise ValueError(
                f"Unknown PROVIDER={explicit!r}. "
                f"Options: {', '.join(list(PRESETS.keys()) + ['auto'])}"
            )
        return PRESETS[explicit]

    # Explicit auto or auto-detected
    available = _available_providers()

    if explicit == "auto" and available:
        return _build_mixed_pool()

    if len(available) > 1:
        return _build_mixed_pool()

    if len(available) == 1:
        return PRESETS[available[0]]

    # Fallback to models_price.json
    if _PRICES_PATH.exists():
        with open(_PRICES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    raise FileNotFoundError(
        "No provider configured. Set PROVIDER in .env or add an API key "
        f"({', '.join(ENV_KEYS.values())})."
    )


def get_budget() -> float:
    """Return BUDGET_PER_CALL from .env as a float. Defaults to 10.0."""
    raw = os.getenv("BUDGET_PER_CALL", "10.0")
    try:
        return float(raw)
    except ValueError:
        raise ValueError(
            f"BUDGET_PER_CALL in .env must be a number, got: {raw!r}"
        )


def get_quality_eval_enabled() -> bool:
    """Whether to run quality evaluation after execute mode. Default: False."""
    return os.getenv("QUALITY_EVAL_ENABLED", "false").lower() in ("true", "1", "yes")


def get_quality_threshold() -> int:
    """Minimum acceptable quality score (1-10). Default: 6."""
    raw = os.getenv("QUALITY_THRESHOLD", "6")
    return max(1, min(10, int(raw)))


def get_quality_max_retries() -> int:
    """Max quality-based retries (model escalations). Default: 2."""
    raw = os.getenv("QUALITY_MAX_RETRIES", "2")
    return max(0, min(5, int(raw)))


def get_judge_model() -> str | None:
    """Override judge model. Default: None (use evaluator default)."""
    raw = os.getenv("JUDGE_MODEL", "").strip()
    return raw or None


def get_api_key(provider: str) -> str:
    """Return the API key for a provider."""
    env_var = ENV_KEYS.get(provider.lower())
    if env_var is None:
        raise KeyError(
            f"Unknown provider {provider!r}. "
            f"Options: {', '.join(ENV_KEYS.keys())}"
        )
    key = os.getenv(env_var)
    if not key:
        raise KeyError(f"{env_var} is not set. Add it to your .env file.")
    return key


if __name__ == "__main__":
    provider = get_active_provider()
    prices = get_model_prices()
    print(f"Provider: {provider}")
    for model_id, info in prices.items():
        src = info.get("provider", "config")
        print(f"  L{info['level']}: {info['display_name']} ({model_id}) — {src}")
    print(f"Budget:   {get_budget()}")
