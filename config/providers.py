"""Pre-configured provider presets for CostAgent multi-provider support.

Each model has:
  - display_name: human-readable name
  - level: task complexity (1=simple, 2=medium, 3=complex)
  - cost_tier: relative cost ranking (1=cheap, 2=mid, 3=expensive)
    Used by auto mode to pick the cheapest L1, balanced L2, strongest L3.
"""

PRESETS = {
    "google": {
        "gemini/gemini-2.0-flash": {"display_name": "Gemini 2.0 Flash", "level": 1, "cost_tier": 1},
        "gemini/gemini-2.5-flash": {"display_name": "Gemini 2.5 Flash", "level": 2, "cost_tier": 1},
        "gemini/gemini-2.5-pro":   {"display_name": "Gemini 2.5 Pro",   "level": 3, "cost_tier": 2},
    },
    "openai": {
        "gpt-4o-mini": {"display_name": "GPT-4o Mini", "level": 1, "cost_tier": 1},
        "gpt-4o":      {"display_name": "GPT-4o",      "level": 2, "cost_tier": 2},
        "o3-mini":     {"display_name": "o3-mini",      "level": 3, "cost_tier": 3},
    },
    "anthropic": {
        "anthropic/claude-haiku-4-5-20251001":  {"display_name": "Claude Haiku",  "level": 1, "cost_tier": 1},
        "anthropic/claude-sonnet-4-20250514":   {"display_name": "Claude Sonnet", "level": 2, "cost_tier": 2},
        "anthropic/claude-opus-4-20250514":     {"display_name": "Claude Opus",   "level": 3, "cost_tier": 3},
    },
    "deepseek": {
        "deepseek/deepseek-chat":     {"display_name": "DeepSeek V3", "level": 1, "cost_tier": 1},
        "deepseek/deepseek-reasoner": {"display_name": "DeepSeek R1", "level": 3, "cost_tier": 1},
    },
}

# Provider name -> environment variable for API key
ENV_KEYS = {
    "google":    "GOOGLE_API_KEY",
    "openai":    "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek":  "DEEPSEEK_API_KEY",
}
