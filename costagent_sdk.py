from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class CostAgentClient:
    """Minimal Python client for calling a CostAgent server via HTTP."""

    base_url: str = "http://localhost:8000"
    timeout_s: float = 30.0
    tenant_id: str | None = None
    caller_id: str | None = None

    def run(
        self,
        *,
        input_text: str,
        level: int = 1,
        tokens: int = 100,
        model: str | None = None,
        budget: float | None = None,
        execute: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "input_text": input_text,
            "level": level,
            "tokens": tokens,
            "execute": execute,
        }
        if model is not None:
            body["model"] = model
        if budget is not None:
            body["budget"] = budget
        if self.tenant_id is not None:
            body["tenant_id"] = self.tenant_id
        if self.caller_id is not None:
            body["caller_id"] = self.caller_id

        r = httpx.post(f"{self.base_url}/api/run", json=body, timeout=self.timeout_s)
        r.raise_for_status()
        return r.json()

