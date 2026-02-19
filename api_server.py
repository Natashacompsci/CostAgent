from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

from config.config import get_active_provider, get_model_prices
from core.agent_loop import AgentLoop
from core.token_estimator import TokenEstimator
from memory.db import get_recent_runs
from utils.helpers import truncate_text
from utils.helpers import build_run_summary
from utils.observability import get_logger, log_event


@asynccontextmanager
async def lifespan(app: FastAPI):
    AgentLoop()   # triggers init_db() via LogHandler.__init__
    provider = get_active_provider() or "custom"
    models = get_model_prices()
    model_list = ", ".join(
        f"{info['display_name']} (L{info['level']})" for info in models.values()
    )
    ops = get_logger("costagent.api")
    log_event(ops, "api_start", provider=provider, models=model_list)
    yield


app = FastAPI(title="CostAgent API", version="0.1.0", lifespan=lifespan)


# --- Pydantic schemas ---

class RunTaskRequest(BaseModel):
    input_text: str
    tenant_id:  str | None     = Field(None,              description="Optional tenant identifier for multi-agent integrations")
    caller_id:  str | None     = Field(None,              description="Optional caller identifier (agent/service) for attribution")
    level:      int            = Field(1,     ge=1, le=3, description="Task complexity level (1-3)")
    tokens:     int            = Field(100,   ge=1,       description="Expected output token count")
    model:      str | None     = Field(None,              description="Override router; null = auto-route")
    budget:     float | None   = Field(None,              description="Per-call budget override")
    execute:    bool           = Field(False,             description="True = call LLM API; False = dry-run estimate only")


class RunTaskResponse(BaseModel):
    trace_id:         str
    model:            str
    prompt_tokens:    int
    output_tokens:    int
    prompt_cost:      float
    completion_cost:  float
    total_cost:       float
    budget:           float
    budget_exceeded:  bool
    cumulative_cost:  float
    log_id:           int
    response:         str
    actual_cost:      float | None
    actual_output_tokens: int | None = None
    summary:          str


class RouteRequest(BaseModel):
    level: int = Field(1, ge=1, le=3, description="Task complexity level (1-3)")
    model: str | None = Field(None, description="Optional override model")


class RouteResponse(BaseModel):
    model: str
    router_reason: str


class EstimateRequest(BaseModel):
    input_text: str
    level:      int            = Field(1,     ge=1, le=3, description="Task complexity level (1-3)")
    tokens:     int            = Field(100,   ge=1,       description="Expected output token count")
    model:      str | None     = Field(None,              description="Override router; null = auto-route")
    budget:     float | None   = Field(None,              description="Per-call budget override")


class EstimateResponse(BaseModel):
    trace_id: str
    model: str
    router_reason: str
    prompt_tokens: int
    output_tokens: int
    prompt_cost: float
    completion_cost: float
    total_cost: float
    budget: float
    budget_exceeded: bool
    compression_ratio: float
    latency_ms: float


# --- Endpoints ---

@app.post("/api/route", response_model=RouteResponse)
def route_task(body: RouteRequest):
    """Return the chosen model for a given task level (no logging)."""
    ops = get_logger("costagent.api")
    agent = AgentLoop()
    if body.model:
        model_name = body.model
        router_reason = f"override:{body.model}"
    else:
        model_name = agent.router.route_task(body.level)
        router_reason = f"router:level={body.level}"

    log_event(ops, "api_route_ok", model=model_name, router_reason=router_reason, level=body.level)
    return RouteResponse(model=model_name, router_reason=router_reason)


@app.post("/api/estimate", response_model=EstimateResponse)
def estimate_task(body: EstimateRequest):
    """Compress + route + estimate cost (no execute, no Memory write)."""
    import time
    import uuid

    ops = get_logger("costagent.api")
    trace_id = str(uuid.uuid4())
    t_start = time.perf_counter()

    agent = AgentLoop()
    effective_budget = body.budget if body.budget is not None else agent.budget

    compressed = agent.compressor.compress(body.input_text)
    if body.model:
        model_name = body.model
        router_reason = f"override:{body.model}"
    else:
        model_name = agent.router.route_task(body.level)
        router_reason = f"router:level={body.level}"

    estimate = TokenEstimator().estimate(compressed, body.tokens, model_name)
    budget_exceeded = estimate["total_cost"] > effective_budget
    compression_ratio = (len(compressed) / len(body.input_text)) if body.input_text else 1.0

    t_end = time.perf_counter()
    latency_ms = (t_end - t_start) * 1000.0

    log_event(
        ops,
        "api_estimate_ok",
        trace_id=trace_id,
        level=body.level,
        model=model_name,
        router_reason=router_reason,
        budget=effective_budget,
        budget_exceeded=budget_exceeded,
        latency_ms=latency_ms,
        prompt_preview=truncate_text(body.input_text, max_chars=80),
    )

    return EstimateResponse(
        trace_id=trace_id,
        model=model_name,
        router_reason=router_reason,
        prompt_tokens=estimate["prompt_tokens"],
        output_tokens=estimate["output_tokens"],
        prompt_cost=estimate["prompt_cost"],
        completion_cost=estimate["completion_cost"],
        total_cost=estimate["total_cost"],
        budget=effective_budget,
        budget_exceeded=budget_exceeded,
        compression_ratio=compression_ratio,
        latency_ms=latency_ms,
    )


@app.post("/api/run", response_model=RunTaskResponse)
def run_task(body: RunTaskRequest):
    """Route a prompt, estimate cost, log the run, and return the result."""
    ops = get_logger("costagent.api")
    try:
        agent = AgentLoop()
        result = agent.run_task(
            prompt=body.input_text,
            expected_output_tokens=body.tokens,
            task_level=body.level,
            model_override=body.model,
            budget_override=body.budget,
            execute=body.execute,
        )
        # Attach attribution fields for Memory without changing core behavior.
        if body.tenant_id is not None:
            result["tenant_id"] = body.tenant_id
        if body.caller_id is not None:
            result["caller_id"] = body.caller_id
    except Exception as e:
        msg = str(e)
        # Extract the key error message, strip verbose litellm stack traces
        if "\n" in msg:
            msg = msg.split("\n")[0]
        ops.exception("api_run_error", extra={"extra_fields": {"event": "api_run_error"}})
        raise HTTPException(status_code=500, detail=msg)

    log_event(
        ops,
        "api_run_ok",
        trace_id=result.get("trace_id"),
        model=result.get("model"),
        status=result.get("status"),
        log_id=result.get("log_id"),
    )
    return RunTaskResponse(
        **{k: result[k] for k in RunTaskResponse.model_fields if k != "summary"},
        summary=build_run_summary(result),
    )


@app.get("/api/runs")
def list_runs(limit: int = 10):
    """Return the most recent task runs from the log."""
    return {"runs": get_recent_runs(limit)}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
