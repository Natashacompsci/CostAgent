# CostAgent — Implementation Plan & Upgrade Roadmap

> This document serves as the single source of truth for the project's technical architecture,
> implementation plan, and long-term product roadmap. Refer to it before starting any new feature
> or refactoring work.

---

## 1. Product Vision

CostAgent is a lightweight Token Cost Optimization & Model Routing Agent that:
- Estimates LLM API costs **before** making calls
- Routes tasks to the optimal model based on complexity level
- **Cross-provider smart routing** — auto-selects the best model across all configured providers
- Compresses prompts to reduce token usage
- Logs all runs for budget tracking and historical analysis
- Provides a foundation for enterprise templates and agent integration

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────┐
│                  CLI / Typer                          │
│  subcommands: run-task | history | budget-check      │
│               providers                              │
│  --model --budget --input-file --output-file         │
└──────────────────────┬───────────────────────────────┘
                       │ HTTP POST /api/run
                       ▼
┌──────────────────────────────────────────────────────┐
│               API Server (FastAPI)                    │
│  POST /api/run   GET /api/runs   GET /health          │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│                    Core                               │
│   TokenEstimator  SemanticCompressor                  │
│   ProbabilisticRouter                                 │
│              └──────────────┐                         │
│                   ┌─────────▼──────────────┐          │
│                   │      AgentLoop          │          │
│                   │  (self-feedback loop)   │◀────────┤
│                   └─────────┬──────────────┘          │
└─────────────────────────────┼─────────────────────────┘
                              │ query / update
                              ▼
┌──────────────────────────────────────────────────────┐
│                   Memory                              │
│   memory/db.py   (sqlite-utils, task_log.db)          │
│   memory/log_handler.py                               │
└──────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────┐
│               Operational logs (stdout)               │
│   utils/observability.py (JSON lines + stack traces)  │
│   correlated with Memory via trace_id                 │
└──────────────────────────────────────────────────────┘
                              ▲
                              │ config
┌──────────────────────────────────────────────────────┐
│                   Config                              │
│   config/providers.py   (4 provider presets)          │
│   config/config.py      (auto-detect + mixed routing) │
│   config/models_price.json (user custom override)     │
│   .env                  (API keys + PROVIDER + BUDGET) │
└──────────────────────────────────────────────────────┘
```

**Key design decisions:**
- **CLI → API → Core → Memory** — single entry point through the API; CLI is a thin HTTP client
- **Self-feedback loop** — AgentLoop queries Memory after each run to report cumulative cost
- **Memory encapsulated in Core** — CLI and API never touch the database directly
- **Two logging systems** — Business Memory (SQLite) for durable analytics/training; Operational logs (stdout) for debugging/observability. Linked by `trace_id`.
- **Cross-provider routing** — Config layer auto-detects available API keys and builds optimal model pool
- **Three-layer config priority** — `PROVIDER` env var > auto-detect from keys > `models_price.json`

---

## 3. Tech Stack & Open-Source Libraries

| Layer | Library | Purpose |
|---|---|---|
| LLM unified API | `litellm` | Token counting, cost estimation, multi-provider API calls |
| Token counting | `tiktoken` | Tokenizer (used by litellm internally) |
| Prompt trimming | `langchain-text-splitters` | `TokenTextSplitter` for hard token limits |
| Business Memory | `sqlite-utils` | Lightweight SQLite ORM for durable run records (analytics/training) |
| Operational logs | stdlib `logging` | JSON lines + stack traces to stdout (observability) |
| Config / env | `python-dotenv` | `.env` file loading |
| CLI | `typer` + `httpx` | CLI framework + HTTP client |
| API | `fastapi` + `pydantic` | REST API + request/response validation |
| API tests | FastAPI `TestClient` | Integration testing |

**`requirements.txt`:**
```
typer>=0.9
fastapi>=0.100
uvicorn>=0.23
tiktoken>=0.5
python-dotenv>=1.0
sqlite-utils>=3.35
langchain-text-splitters>=0.2
httpx>=0.24
litellm>=1.0
```

---

## 4. Multi-Provider Support

### Supported Providers

| Provider | Env Variable | L1 (Simple) | L2 (Medium) | L3 (Complex) |
|----------|-------------|-------------|-------------|--------------|
| Google | `GOOGLE_API_KEY` | Gemini 2.0 Flash | Gemini 2.5 Flash | Gemini 2.5 Pro |
| OpenAI | `OPENAI_API_KEY` | GPT-4o Mini | GPT-4o | o3-mini |
| Anthropic | `ANTHROPIC_API_KEY` | Claude Haiku | Claude Sonnet | Claude Opus |
| DeepSeek | `DEEPSEEK_API_KEY` | DeepSeek V3 | _(fallback)_ | DeepSeek R1 |

### Routing Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Auto (mixed)** | Multiple API keys set | Cross-provider: cheapest L1, best-value L2, strongest L3 |
| **Single provider** | One key set, or `PROVIDER=xxx` | Routes within that provider only |
| **Custom** | Edit `models_price.json` | Any litellm-supported model |

### Auto Mode Selection Logic

Each model has a `cost_tier` (1=cheap, 2=mid, 3=expensive):
- **L1**: picks model with lowest `cost_tier` across all available providers
- **L2**: picks median `cost_tier` model
- **L3**: picks highest `cost_tier` model (strongest)

---

## 5. Project Structure

```
CostAgent/
├── docs/
│   └── IMPLEMENTATION_PLAN.md    # this file
├── config/
│   ├── providers.py              # 4 provider presets with cost_tier
│   ├── config.py                 # auto-detect, mixed routing, get_model_prices()
│   └── models_price.json         # user custom override (fallback)
├── core/
│   ├── __init__.py
│   ├── token_estimator.py        # litellm-based cost estimation
│   ├── semantic_compressor.py    # stopword removal + whitespace collapse
│   ├── probabilistic_router.py   # level → model name mapping
│   └── agent_loop.py             # orchestrator with self-feedback loop
├── memory/
│   ├── db.py                     # sqlite-utils database layer
│   └── log_handler.py            # adapter between AgentLoop results and db
├── utils/
│   ├── helpers.py                # format_cost, build_run_summary, utc_now_iso
│   ├── observability.py          # operational logs (stdout), JSON events, exceptions
│   ├── prompt_cleaner.py         # strip HTML, normalize unicode, collapse whitespace
│   └── prompt_trimmer.py         # TokenTextSplitter wrapper for hard token limits
├── tests/
│   ├── test_token_estimator.py
│   ├── test_compressor.py
│   ├── test_router.py
│   └── test_api.py               # FastAPI TestClient integration tests
├── examples/
│   ├── test_tasks.md             # 70+ test commands across 10 agent types
│   └── test_doc.txt
├── main.py                       # Typer CLI (thin httpx client)
├── api_server.py                 # FastAPI server (central broker)
├── requirements.txt
├── .env                          # API keys + PROVIDER + BUDGET_PER_CALL
├── .env.example
└── README.md
```

---

## 6. Implementation History

### v0.1 — MVP (completed)

Core pipeline: compress → route → estimate → budget-check → log.
CLI + API server + Memory layer + unit tests.

### v0.1.1 — litellm Integration (completed)

- Replaced manual tiktoken pricing with `litellm.cost_per_token()` + `litellm.token_counter()`
- Added execute mode via `litellm.completion()` — real API calls with actual cost tracking
- Gemini test configuration (free tier)
- Budget guard with per-call limit
- Estimated vs actual cost comparison
- Fixed cost estimation accuracy (was 200-800x off due to `cost_per_token()` API misuse)
- Empty response handling for Gemini 2.5 Pro
- Error message cleanup (strip verbose litellm stack traces)
- History shows actual_cost for executed runs
- Budget-check shows estimated vs actual totals

### v0.1.2 — Multi-Provider Support (completed)

- 4 provider presets: Google, OpenAI, Anthropic, DeepSeek
- Auto-detect available API keys from `.env`
- **Cross-provider mixed routing** — when multiple keys present, auto-selects best model per level
- `cost_tier` field for cross-provider cost comparison
- `PROVIDER` env var for explicit provider selection
- `providers` CLI command to view current routing and all presets
- API server prints provider info on startup
- Open-source readiness: `.env.example`, README rewrite, GPL-3.0 license

---

## 7. Upgrade Roadmap

| Version | Milestone | What to build | Status |
|---|---|---|---|
| **v0.1** | MVP | Core + CLI + API + logging | Done |
| **v0.1.1** | Real API calls | litellm integration, execute mode, cost tracking | Done |
| **v0.1.2** | Multi-provider | Cross-provider routing, auto-detect, 4 presets | Done |
| **v0.2** | Enterprise templates | `config/templates/*.json` + `/api/run/template/{id}` | Planned |
| **v0.3** | Agent integration | Webhook endpoint + Slack example + multi-step chaining | Planned |
| **v0.4** | Historical routing | Replace heuristic with model trained on `task_log.db` | Planned |
| **v1.0** | Cloud + SLA | Docker + gunicorn, auth middleware, rate limiting | Planned |

### How each version builds on the previous:

```
v0.1 (MVP)
  └─ v0.1.1 (litellm)         ← real API calls, cost tracking
       └─ v0.1.2 (Multi-provider) ← cross-provider smart routing
            └─ v0.2 (Templates)    ← templates call AgentLoop.run_task()
                 └─ v0.3 (Integration)  ← Slack, CRM, webhook
                      └─ v0.4 (Smart routing)  ← ML-based from task_log.db
                           └─ v1.0 (Cloud)     ← Docker, auth, rate limiting
```

---

## 8. Interface Contracts

### CLI Interface

| Subcommand | Description |
|---|---|
| `run-task` | Route, estimate, optionally execute a task |
| `history` | Show recent runs from the log |
| `budget-check` | Show cumulative cost (estimated + actual) |
| `providers` | Show current provider routing or list all presets |

| Flag | Short | Description |
|---|---|---|
| `--prompt` | `-p` | Inline prompt text |
| `--input-file` | `-f` | Read prompt from file |
| `--output-file` | `-o` | Save full result JSON to file |
| `--tokens` | `-t` | Expected output token count |
| `--level` | `-l` | Task complexity level (1-3) |
| `--model` | `-m` | Override router, use this model directly |
| `--budget` | `-b` | Per-call budget override |
| `--execute` | `-e` | Actually call the LLM API |

### API Interface

| Field | Type | Required | Description |
|---|---|---|---|
| `input_text` | string | yes | The prompt text |
| `level` | int (1-3) | no, default 1 | Task complexity level |
| `tokens` | int | no, default 100 | Expected output tokens |
| `model` | string | no | Override router; `null` = auto-route |
| `budget` | float | no | Per-call budget override |
| `execute` | bool | no, default false | True = call LLM API; False = dry-run estimate only |

Response includes: `model`, `prompt_tokens`, `output_tokens`, `prompt_cost`, `completion_cost`,
`total_cost`, `budget`, `budget_exceeded`, `cumulative_cost`, `log_id`, `response`, `actual_cost`,
`actual_output_tokens`, `summary`

---

## 9. Extensibility Hooks (built into MVP, implemented later)

### 9.1 Enterprise Templates

Pre-built prompt + model + level bundles for common business tasks.

```json
{
  "id":            "doc-summary",
  "description":   "Condense a contract or report into key bullet points",
  "system_prompt": "You are an expert summarizer...",
  "level":          1,
  "tokens":         300
}
```

New endpoint: `POST /api/run/template/{template_id}`
New CLI: `python3 main.py run-template --template doc-summary --input-file contract.txt`

### 9.2 Agent Integration

| Integration | How it calls CostAgent |
|---|---|
| **Slack bot** | Webhook → `POST /api/run/template/{id}` |
| **CRM trigger** | HTTP call to `/api/run` |
| **CLI automation / cron** | `--input-file` + `--output-file` |
| **Multi-step chain** | Feed `result["response"]` as next prompt |

---

## 10. Design Principles

1. **Config over code** — adding a model or provider should only require config changes
2. **Core is sacred** — `AgentLoop.run_task()` is the single orchestration method; don't bypass it
3. **Memory is internal** — only AgentLoop reads/writes the database; CLI and API go through Core
3a. **Operational logs are separate** — stack traces and fine-grained events go to stdout logs, not SQLite
4. **CLI is a thin client** — it calls the API via HTTP; it never imports Core or Memory
5. **Tests mock prices** — inject a fixture dict into constructors; never read from filesystem in tests
6. **Provider-agnostic core** — Core, Memory, and Utils have zero provider-specific logic

---

## 11. Environments & Observability

### 11.1 Multi-environment Memory

CostAgent supports multi-environment deployments by tagging each run with `env_name` and allowing the
SQLite path to be overridden.

| Variable | Default | Purpose |
|---|---|---|
| `ENV_NAME` | `dev` | Tag each run for multi-environment analysis (dev/staging/prod) |
| `TASK_LOG_DB_PATH` | `memory/task_log.db` | Override SQLite path (recommended in Docker/production) |

### 11.2 Operational logs (stdout)

Operational logs are emitted as structured JSON lines to stdout and are intended for debugging and
production observability. They include fine-grained lifecycle events and full exception stack traces.

| Variable | Default | Purpose |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Operational log verbosity |
| `LOG_JSON` | `true` | Emit operational logs as JSON lines to stdout |

**Correlation**: both Business Memory and operational logs share the same `trace_id`.
