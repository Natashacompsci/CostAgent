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
- **Quality evaluation with auto-fallback** — LLM-as-judge scores output quality, auto-escalates to stronger model on low scores
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
│   ProbabilisticRouter  QualityEvaluator               │
│              └──────────────┐                         │
│                   ┌─────────▼──────────────┐          │
│                   │      AgentLoop          │          │
│                   │  (self-feedback loop)   │◀────────┤
│                   │  (quality retry loop)   │          │
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
│   ├── IMPLEMENTATION_PLAN.md    # this file (private, not on GitHub)
│   └── INTEGRATIONS.md           # integration guide for all methods
├── config/
│   ├── providers.py              # 4 provider presets with cost_tier
│   ├── config.py                 # auto-detect, mixed routing, get_model_prices()
│   └── models_price.json         # user custom override (fallback)
├── core/
│   ├── __init__.py
│   ├── token_estimator.py        # litellm-based cost estimation
│   ├── semantic_compressor.py    # stopword removal + whitespace collapse
│   ├── probabilistic_router.py   # level → model name mapping
│   ├── quality_evaluator.py      # LLM-as-judge quality scoring + fail-open
│   └── agent_loop.py             # orchestrator with self-feedback + quality retry loop
├── memory/
│   ├── db.py                     # sqlite-utils database layer
│   └── log_handler.py            # adapter between AgentLoop results and db
├── utils/
│   ├── helpers.py                # format_cost, build_run_summary, utc_now_iso
│   ├── observability.py          # operational logs (stdout), JSON events, exceptions
│   ├── prompt_cleaner.py         # strip HTML, normalize unicode, collapse whitespace
│   └── prompt_trimmer.py         # TokenTextSplitter wrapper for hard token limits
├── integrations/
│   ├── openai_tools.py           # OpenAI-compatible tool schemas + dispatch
│   ├── langchain_tools.py        # LangChain StructuredTool wrappers
│   └── openclaw/
│       ├── SKILL.md              # OpenClaw skill definition
│       └── README.md             # OpenClaw installation guide
├── tests/
│   ├── test_token_estimator.py
│   ├── test_compressor.py
│   ├── test_router.py
│   ├── test_quality.py            # quality evaluator + retry flow tests
│   └── test_api.py               # FastAPI TestClient integration tests
├── examples/
│   ├── test_tasks.md             # 70+ test commands across 10 agent types
│   └── test_doc.txt
├── main.py                       # Typer CLI (thin httpx client)
├── api_server.py                 # FastAPI server (central broker)
├── costagent_sdk.py              # Python SDK (thin httpx wrapper)
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

### v0.1.3 — Agent Native (completed)

- **Structured error model** — `ErrorResponse` schema with machine-readable `error_code` (`provider_unavailable`, `provider_auth_error`, `internal_error`), proper HTTP status codes (502 for provider errors, 500 for internal)
- **Error classification** — `_classify_error()` auto-detects error type from exception class name and message keywords
- **OpenClaw Skill** — `integrations/openclaw/SKILL.md` for one-click integration with the OpenClaw AI agent framework
- **Integration docs** — `docs/INTEGRATIONS.md` covering all 5 integration methods (HTTP, Python SDK, OpenAI tools, LangChain, OpenClaw)
- **README rewrite** — open-core style: public-facing product page without exposing internal algorithm details
- Already had (from v0.1.2): `tenant_id`/`caller_id` multi-tenant fields, `costagent_sdk.py`, OpenAI tools wrapper, LangChain tools wrapper

### v0.1.4 — Quality Evaluation & Auto-Fallback (completed)

- **LLM-as-judge quality gate** — uses a cheap judge model (Gemini Flash by default) to score LLM output 1-10 on relevance, completeness, accuracy, and clarity
- **Auto-escalation retry loop** — if quality score < threshold, auto-escalates L1→L2→L3 and retries with a stronger model
- **Fail-open design** — on any judge error (network, parse, timeout), returns score=10 so the pipeline is never blocked
- **Three-tier response parsing** — JSON → regex fallback → fail-open (score=10)
- **Configurable via env vars** — disabled by default (`QUALITY_EVAL_ENABLED=false`); zero overhead when off
- **Input truncation** — judge inputs are truncated (2000/3000 chars) to control evaluation cost
- **5 new Memory fields** — `quality_score`, `quality_reason`, `quality_retries`, `quality_eval_cost`, `original_model` auto-added via `alter=True`
- **Config getters** — `get_quality_eval_enabled()`, `get_quality_threshold()`, `get_quality_max_retries()`, `get_judge_model()` following existing `get_budget()` pattern
- **13 new tests** — `_parse_score()` unit tests, `evaluate()` mocked tests, integration tests for retry flow with alternating task/judge mock responses

---

## 7. Upgrade Roadmap

| Version | Milestone | What to build | Status |
|---|---|---|---|
| **v0.1** | MVP | Core + CLI + API + logging | Done |
| **v0.1.1** | Real API calls | litellm integration, execute mode, cost tracking | Done |
| **v0.1.2** | Multi-provider | Cross-provider routing, auto-detect, 4 presets | Done |
| **v0.1.3** | Agent Native | Structured errors, OpenClaw skill, integration docs | Done |
| **v0.1.4** | Quality Gate | LLM-as-judge eval, auto-fallback retry, fail-open | Done |
| **v0.2** | Enterprise templates | `config/templates/*.json` + `/api/run/template/{id}` | Planned |
| **v0.3** | Deep integration | Webhook endpoint + Slack example + multi-step chaining | Planned |
| **v0.4** | Historical routing | Replace heuristic with model trained on `task_log.db` | Planned |
| **v1.0** | Cloud + SLA | Docker + gunicorn, auth middleware, rate limiting | Planned |

### How each version builds on the previous:

```
v0.1 (MVP)
  └─ v0.1.1 (litellm)            ← real API calls, cost tracking
       └─ v0.1.2 (Multi-provider)   ← cross-provider smart routing
            └─ v0.1.3 (Agent Native)    ← structured errors, integrations, OpenClaw
                 └─ v0.1.4 (Quality Gate)    ← LLM-as-judge, auto-fallback retry
                      └─ v0.2 (Templates)       ← templates call AgentLoop.run_task()
                      └─ v0.3 (Integration)   ← Slack, CRM, webhook
                           └─ v0.4 (Smart routing)  ← ML-based from task_log.db
                                └─ v1.0 (Cloud)     ← Docker, auth, rate limiting
```

---

## 8. Agent Native Architecture

### Integration Layer

CostAgent exposes five integration methods, all calling the same Core via HTTP:

```
                    ┌─────────────────────┐
                    │     Core (private)   │
                    │  AgentLoop           │
                    │  SemanticCompressor  │
                    │  ProbabilisticRouter │
                    │  TokenEstimator      │
                    └─────────┬───────────┘
                              │
                    ┌─────────▼───────────┐
                    │  API Server (public) │
                    │  /api/run            │
                    │  /api/estimate       │
                    │  /api/route          │
                    └─────────┬───────────┘
                              │
        ┌─────────┬───────────┼───────────┬──────────┐
        ▼         ▼           ▼           ▼          ▼
   Python SDK  OpenAI    LangChain   OpenClaw     Raw HTTP
              tools      tools       Skill       (curl, etc.)
```

### Multi-Tenant Attribution

All integration methods support `tenant_id` and `caller_id`:
- Passed in request body (API) or constructor (SDK)
- Persisted to Memory for per-caller analytics and cost allocation
- Fields are optional — omitting them has zero impact on existing behavior

### Structured Error Model

Error responses use `ErrorResponse` schema instead of raw `HTTPException`:

| error_code | HTTP status | Trigger |
|---|---|---|
| `provider_auth_error` | 502 | Invalid/missing API key, authentication failure |
| `provider_unavailable` | 502 | Provider timeout, rate limit, connection error |
| `internal_error` | 500 | Unexpected exception in Core |

Classification is done by `_classify_error()` in `api_server.py`, which inspects exception class name
and message keywords against `_PROVIDER_KEYWORDS`.

**Design decision:** 200 responses (including `budget_exceeded=True` and `status="dry_run"`) are
unchanged. Error responses are the only breaking change vs. pre-v0.1.3, and only in the JSON structure
(was `{"detail": "..."}`, now `{"error_code": "...", "message": "...", ...}`).

### Open-Core Boundary

| Public (GitHub) | Private (this doc) |
|---|---|
| API contract, CLI usage, integration examples | Core algorithms, routing logic, compressor internals |
| `costagent_sdk.py`, `integrations/` | `core/agent_loop.py`, `core/semantic_compressor.py` |
| `config/models_price.json` schema | `config/providers.py` cost_tier selection logic |
| Quality eval feature description + config vars | `core/quality_evaluator.py` judge prompt, `_parse_score()`, retry algorithm |
| README.md, docs/INTEGRATIONS.md | docs/IMPLEMENTATION_PLAN.md |

---

## 9. Interface Contracts (moved from README — private)

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
`actual_output_tokens`, `quality_score`, `quality_reason`, `quality_retries`, `quality_eval_cost`,
`original_model`, `summary`

---

## 10. Extensibility Hooks (built into MVP, implemented later)

### 10.1 Enterprise Templates

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

### 10.2 Agent Integration

| Integration | How it calls CostAgent |
|---|---|
| **Slack bot** | Webhook → `POST /api/run/template/{id}` |
| **CRM trigger** | HTTP call to `/api/run` |
| **CLI automation / cron** | `--input-file` + `--output-file` |
| **Multi-step chain** | Feed `result["response"]` as next prompt |

---

## 11. Design Principles

1. **Config over code** — adding a model or provider should only require config changes
2. **Core is sacred** — `AgentLoop.run_task()` is the single orchestration method; don't bypass it
3. **Memory is internal** — only AgentLoop reads/writes the database; CLI and API go through Core
3a. **Operational logs are separate** — stack traces and fine-grained events go to stdout logs, not SQLite
4. **CLI is a thin client** — it calls the API via HTTP; it never imports Core or Memory
5. **Tests mock prices** — inject a fixture dict into constructors; never read from filesystem in tests
6. **Provider-agnostic core** — Core, Memory, and Utils have zero provider-specific logic

---

## 12. Environments & Observability

### 12.1 Multi-environment Memory

CostAgent supports multi-environment deployments by tagging each run with `env_name` and allowing the
SQLite path to be overridden.

| Variable | Default | Purpose |
|---|---|---|
| `ENV_NAME` | `dev` | Tag each run for multi-environment analysis (dev/staging/prod) |
| `TASK_LOG_DB_PATH` | `memory/task_log.db` | Override SQLite path (recommended in Docker/production) |

### 12.2 Quality Evaluation

| Variable | Default | Purpose |
|---|---|---|
| `QUALITY_EVAL_ENABLED` | `false` | Enable LLM-as-judge quality scoring (disabled = zero overhead) |
| `QUALITY_THRESHOLD` | `6` | Minimum score (1-10) to accept a response without retry |
| `QUALITY_MAX_RETRIES` | `2` | Max escalation retries (L1→L2→L3) on low quality |
| `JUDGE_MODEL` | `gemini/gemini-2.0-flash` | litellm model ID for the judge (cheapest by default) |

**Retry flow:** execute → judge scores → if score < threshold and level < 3, escalate model and retry → repeat up to `QUALITY_MAX_RETRIES` times. Final response is always the last attempt regardless of score.

**Fail-open:** any judge error (network, parse, timeout) returns score=10 so the main pipeline is never blocked.

**Memory fields:** `quality_score`, `quality_reason`, `quality_retries`, `quality_eval_cost`, `original_model` — auto-added to SQLite via `alter=True`.

### 12.3 Operational logs (stdout)

Operational logs are emitted as structured JSON lines to stdout and are intended for debugging and
production observability. They include fine-grained lifecycle events and full exception stack traces.

| Variable | Default | Purpose |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Operational log verbosity |
| `LOG_JSON` | `true` | Emit operational logs as JSON lines to stdout |

**Correlation**: both Business Memory and operational logs share the same `trace_id`.
