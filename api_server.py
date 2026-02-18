from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

from core.agent_loop import AgentLoop
from memory.db import get_recent_runs
from utils.helpers import build_run_summary


@asynccontextmanager
async def lifespan(app: FastAPI):
    AgentLoop()   # triggers init_db() via LogHandler.__init__
    yield


app = FastAPI(title="CostAgent API", version="0.1.0", lifespan=lifespan)


# --- Pydantic schemas ---

class RunTaskRequest(BaseModel):
    input_text: str
    level:      int            = Field(1,     ge=1, le=3, description="Task complexity level (1-3)")
    tokens:     int            = Field(100,   ge=1,       description="Expected output token count")
    model:      str | None     = Field(None,              description="Override router; null = auto-route")
    budget:     float | None   = Field(None,              description="Per-call budget override")
    execute:    bool           = Field(False,             description="True = call LLM API; False = dry-run estimate only")


class RunTaskResponse(BaseModel):
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
    summary:          str


# --- Endpoints ---

@app.post("/api/run", response_model=RunTaskResponse)
def run_task(body: RunTaskRequest):
    """Route a prompt, estimate cost, log the run, and return the result."""
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
