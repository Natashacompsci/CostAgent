from __future__ import annotations

from typing import Any, Literal

import httpx

ToolName = Literal["costagent_route", "costagent_estimate", "costagent_run"]


def get_tools() -> list[dict[str, Any]]:
    """Return OpenAI-style tool definitions for CostAgent.

    These schemas are intentionally small and stable so other agent frameworks
    can reuse them as a de-facto standard tool contract.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "costagent_route",
                "description": "Select the best model for a given task level (no execution, no DB write).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "integer", "minimum": 1, "maximum": 3},
                        "model": {"type": ["string", "null"], "description": "Optional override model id"},
                    },
                    "required": ["level"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "costagent_estimate",
                "description": "Compress + route + estimate cost (no execution, no DB write).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input_text": {"type": "string"},
                        "level": {"type": "integer", "minimum": 1, "maximum": 3},
                        "tokens": {"type": "integer", "minimum": 1},
                        "model": {"type": ["string", "null"], "description": "Optional override model id"},
                        "budget": {"type": ["number", "null"], "description": "Optional per-call budget override"},
                    },
                    "required": ["input_text", "level", "tokens"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "costagent_run",
                "description": "Route + estimate + optionally execute. Writes a run record to Memory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input_text": {"type": "string"},
                        "tenant_id": {"type": ["string", "null"]},
                        "caller_id": {"type": ["string", "null"]},
                        "level": {"type": "integer", "minimum": 1, "maximum": 3},
                        "tokens": {"type": "integer", "minimum": 1},
                        "model": {"type": ["string", "null"], "description": "Optional override model id"},
                        "budget": {"type": ["number", "null"], "description": "Optional per-call budget override"},
                        "execute": {"type": "boolean"},
                    },
                    "required": ["input_text", "level", "tokens", "execute"],
                    "additionalProperties": False,
                },
            },
        },
    ]


def dispatch(
    *,
    base_url: str,
    tool_name: ToolName,
    arguments: dict[str, Any],
    timeout_s: float = 30.0,
) -> dict[str, Any]:
    """Dispatch a tool call to the appropriate CostAgent HTTP endpoint."""
    if tool_name == "costagent_route":
        endpoint = "/api/route"
    elif tool_name == "costagent_estimate":
        endpoint = "/api/estimate"
    elif tool_name == "costagent_run":
        endpoint = "/api/run"
    else:
        raise ValueError(f"Unknown tool_name: {tool_name!r}")

    r = httpx.post(f"{base_url}{endpoint}", json=arguments, timeout=timeout_s)
    r.raise_for_status()
    return r.json()

