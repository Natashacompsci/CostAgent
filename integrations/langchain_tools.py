from __future__ import annotations

from typing import Any, List

from integrations.openai_tools import dispatch


def get_langchain_tools(
    base_url: str = "http://localhost:8000",
    *,
    tenant_id: str | None = None,
    caller_id: str | None = None,
) -> List[Any]:
    """Return LangChain-compatible tools that call CostAgent.

    Dependencies are imported lazily so this module does not hard-require
    LangChain/Pydantic unless you actually call this function.
    """
    try:
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel, Field
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "get_langchain_tools() requires 'langchain-core' and 'pydantic' "
            "to be installed."
        ) from exc

    # --- Input models ---

    class RouteInput(BaseModel):
        level: int = Field(..., ge=1, le=3, description="Task complexity level (1-3)")
        model: str | None = Field(
            default=None, description="Optional override model id (bypass router)"
        )

    class EstimateInput(BaseModel):
        input_text: str
        level: int = Field(..., ge=1, le=3)
        tokens: int = Field(..., ge=1)
        model: str | None = None
        budget: float | None = None

    class RunInput(BaseModel):
        input_text: str
        level: int = Field(..., ge=1, le=3)
        tokens: int = Field(..., ge=1)
        execute: bool = False
        model: str | None = None
        budget: float | None = None

    # --- Tool callables ---

    def _route_tool(args: RouteInput) -> dict[str, Any]:
        return dispatch(
            base_url=base_url,
            tool_name="costagent_route",
            arguments=args.dict(),
        )

    def _estimate_tool(args: EstimateInput) -> dict[str, Any]:
        return dispatch(
            base_url=base_url,
            tool_name="costagent_estimate",
            arguments=args.dict(),
        )

    def _run_tool(args: RunInput) -> dict[str, Any]:
        payload = args.dict()
        if tenant_id is not None:
            payload["tenant_id"] = tenant_id
        if caller_id is not None:
            payload["caller_id"] = caller_id
        return dispatch(
            base_url=base_url,
            tool_name="costagent_run",
            arguments=payload,
        )

    # --- Structured tools ---

    tools: List[Any] = [
        StructuredTool.from_function(
            _route_tool,
            name="costagent_route",
            description="Select the best model for a given task level (no execution, no DB write).",
            args_schema=RouteInput,
        ),
        StructuredTool.from_function(
            _estimate_tool,
            name="costagent_estimate",
            description="Compress + route + estimate cost (no execution, no DB write).",
            args_schema=EstimateInput,
        ),
        StructuredTool.from_function(
            _run_tool,
            name="costagent_run",
            description="Route + estimate + optionally execute via CostAgent.",
            args_schema=RunInput,
        ),
    ]

    return tools

