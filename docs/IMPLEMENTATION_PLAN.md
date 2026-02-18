# CostAgent — Implementation Plan & Upgrade Roadmap

> This document serves as the single source of truth for the project's technical architecture,
> implementation plan, and long-term product roadmap. Refer to it before starting any new feature
> or refactoring work.

---

## 1. Product Vision

CostAgent is a lightweight Token Cost Optimization & Model Routing Agent that:
- Estimates LLM API costs **before** making calls
- Routes tasks to the optimal model based on complexity level
- Compresses prompts to reduce token usage
- Logs all runs for budget tracking and historical analysis
- Provides a foundation for enterprise templates and agent integration

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────┐
│                  CLI / Typer                          │
│  subcommands: run-task | history | budget-check       │
│  --model --budget --input-file --output-file          │
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
```

**Key design decisions:**
- **CLI → API → Core → Memory** — single entry point through the API; CLI is a thin HTTP client
- **Self-feedback loop** — AgentLoop queries Memory after each run to report cumulative cost
- **Memory encapsulated in Core** — CLI and API never touch the database directly

---

## 3. Tech Stack & Open-Source Libraries

| Layer | Library | What it replaces |
|---|---|---|
| Token counting | `tiktoken` | word `.split()` heuristic |
| Prompt trimming | `langchain-text-splitters` (`TokenTextSplitter`) | manual tiktoken encode/slice/decode |
| DB / logging | `sqlite-utils` | raw sqlite3 SQL boilerplate |
| Config / env | `python-dotenv` | manual `os.environ` reads |
| CLI | `typer` + `httpx` | argparse + urllib |
| API | `fastapi` + `pydantic` | manual HTTP handling |
| API tests | FastAPI `TestClient` (httpx) | custom test harness |

**`requirements.txt`:**
```
typer
fastapi
uvicorn
tiktoken
python-dotenv
sqlite-utils
langchain-text-splitters
httpx
```

---

## 4. Project Structure

```
CostAgent/
├── docs/
│   └── IMPLEMENTATION_PLAN.md    # this file
├── config/
│   ├── models_price.json         # model pricing table
│   └── config.py                 # loads JSON + .env, exposes get_model_prices() etc.
├── core/
│   ├── __init__.py
│   ├── token_estimator.py        # tiktoken-based cost estimation
│   ├── semantic_compressor.py    # stopword removal + whitespace collapse
│   ├── probabilistic_router.py   # level → model name mapping
│   └── agent_loop.py             # orchestrator with self-feedback loop
├── memory/
│   ├── db.py                     # sqlite-utils database layer
│   └── log_handler.py            # adapter between AgentLoop results and db
├── utils/
│   ├── helpers.py                # format_cost, build_run_summary, utc_now_iso
│   ├── prompt_cleaner.py         # strip HTML, normalize unicode, collapse whitespace
│   └── prompt_trimmer.py         # TokenTextSplitter wrapper for hard token limits
├── tests/
│   ├── test_token_estimator.py
│   ├── test_compressor.py
│   ├── test_router.py
│   └── test_api.py               # FastAPI TestClient integration tests
├── examples/
│   └── test_doc.txt
├── main.py                       # Typer CLI (thin httpx client)
├── api_server.py                 # FastAPI server (central broker)
├── requirements.txt
├── .env                          # API keys + BUDGET_PER_CALL
└── README.md
```

---

## 5. MVP Implementation Phases

### Phase 1 — Config Layer

| File | Description |
|---|---|
| `config/models_price.json` | Per-model pricing with `prompt_price_per_1k`, `completion_price_per_1k`, `tiktoken_model` |
| `config/config.py` | `get_model_prices()`, `get_budget()`, `get_api_key()` — loads from JSON + .env |

### Phase 2 — Memory Layer

| File | Description |
|---|---|
| `memory/db.py` | sqlite-utils: `get_db()`, `init_db()`, `insert_run()`, `get_recent_runs()`, `get_cumulative_cost()` |
| `memory/log_handler.py` | `LogHandler` class: `log_run(result, task_level)`, `cumulative_cost()` |

Schema: `id, timestamp, model, task_level, prompt_tokens, output_tokens, prompt_cost, completion_cost, total_cost, budget_exceeded, compressed_prompt, actual_cost, actual_output_tokens`

### Phase 3 — Utils Layer

| File | Description |
|---|---|
| `utils/helpers.py` | `format_cost()`, `truncate_text()`, `build_run_summary()`, `utc_now_iso()` |
| `utils/prompt_cleaner.py` | `PromptCleaner`: `clean()`, `strip_html()`, `normalize_unicode()`, `collapse_whitespace()` |
| `utils/prompt_trimmer.py` | `PromptTrimmer`: wraps `TokenTextSplitter` — `trim_to_token_limit()`, `count_tokens()` |

### Phase 4 — Upgrade Core Classes

| File | Key changes |
|---|---|
| `core/token_estimator.py` | Uses `litellm.token_counter()` + `litellm.cost_per_token()`; returns a **dict** with full cost breakdown |
| `core/probabilistic_router.py` | Config-driven routing from `models_price.json` level field; supports any litellm model ID |
| `core/agent_loop.py` | `execute` mode via `litellm.completion()`; tracks `actual_cost` and `actual_output_tokens`; self-feedback via `LogHandler` |

### Phase 5 — API Server (`api_server.py`)

| Endpoint | Method | Description |
|---|---|---|
| `/api/run` | POST | `{input_text, level, tokens, model?, budget?}` → full result dict |
| `/api/runs` | GET | `?limit=10` → recent task log |
| `/health` | GET | `{"status": "ok"}` |

Request/response validated with Pydantic `BaseModel`.

### Phase 6 — CLI (`main.py`)

Thin HTTP client — does NOT import Core or Memory.

| Subcommand | Description |
|---|---|
| `run-task` | `--prompt` or `--input-file`, `--tokens`, `--level`, `--model`, `--budget`, `--output-file`, `--execute` |
| `history` | `--limit` — show recent runs from the log |
| `budget-check` | Show cumulative cost across all logged runs |

### Phase 7 — Tests

| File | Key tests |
|---|---|
| `tests/test_token_estimator.py` | tiktoken count → int, empty → 0, estimate dict keys, total = prompt+completion, unknown model → 0, cost scales with length |
| `tests/test_compressor.py` | stopwords removed, whitespace collapsed, max_tokens truncates, empty handled |
| `tests/test_router.py` | level 1→DeepSeek-V3, 2→GPT-4o, 3→Claude-3.5, 99→Claude-3.5 |
| `tests/test_api.py` | POST /api/run → 200 + required fields; model override; GET /health; level 4 → 422 |

### Phase 8 — README + Examples

- `README.md`: setup, architecture, CLI reference, API contract, curl examples
- `examples/test_doc.txt`: sample document for CLI demos

---

## 6. Implementation Order (strict dependency order)

```
1.  requirements.txt
2.  config/models_price.json
3.  config/config.py
4.  memory/db.py
5.  utils/helpers.py
6.  memory/log_handler.py
7.  utils/prompt_cleaner.py
8.  utils/prompt_trimmer.py
9.  core/token_estimator.py
10. core/probabilistic_router.py
11. core/agent_loop.py
12. api_server.py
13. main.py
14. tests/test_token_estimator.py
15. tests/test_compressor.py
16. tests/test_router.py
17. tests/test_api.py
18. README.md
19. examples/test_doc.txt
```

---

## 7. Verification Checklist

```bash
pip install -r requirements.txt

# Standalone core sanity check
python3 -m core.agent_loop

# Start server
python3 api_server.py &

# CLI subcommands
python3 main.py run-task --prompt "Summarize this" --tokens 200 --level 2
python3 main.py run-task --input-file examples/test_doc.txt --model GPT-4o --output-file out.json
python3 main.py history --limit 5
python3 main.py budget-check

# Direct API calls
curl -X POST http://localhost:8000/api/run \
     -H "Content-Type: application/json" \
     -d '{"input_text": "Explain quantum computing", "tokens": 150, "level": 3}'
curl http://localhost:8000/api/runs?limit=5
curl http://localhost:8000/health

# All tests pass
python3 -m pytest tests/ -v
```

---

## 8. Interface Contracts

### CLI Interface

| Field | Flag | Description |
|---|---|---|
| subcommand | `run-task` / `history` / `budget-check` | CLI subcommand |
| `--model` | `-m` | Override router, use this model directly |
| `--budget` | `-b` | Per-call budget override |
| `--input-file` | `-f` | Read prompt from file instead of `--prompt` |
| `--output-file` | `-o` | Save full result JSON to file |
| `--prompt` | `-p` | Inline prompt text |
| `--tokens` | `-t` | Expected output token count |
| `--level` | `-l` | Task complexity level (1-3) |

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

**What:** pre-built, out-of-the-box prompt + model + level bundles for common business tasks.
Enterprise users only supply their variable data — no prompt engineering required.

| Template ID | Input | Output | Model (level) |
|---|---|---|---|
| `doc-summary` | contract / report text | bullet-point summary | DeepSeek-V3 (1) |
| `email-reply` | customer question | standard draft reply | GPT-4o (2) |
| `meeting-notes` | raw transcript / notes | structured minutes | GPT-4o (2) |
| `finance-analysis` | spreadsheet / bill text | data insights + flags | Claude-3.5 (3) |

**How it plugs in:**

```
config/
└─ templates/
   ├─ doc-summary.json
   ├─ email-reply.json
   ├─ meeting-notes.json
   └─ finance-analysis.json
```

Each template JSON:
```json
{
  "id":            "doc-summary",
  "description":   "Condense a contract or report into key bullet points",
  "system_prompt": "You are an expert summarizer. Return 3-5 bullet points covering the key points of the following text:",
  "level":          1,
  "tokens":         300
}
```

New API endpoint:
```python
@app.post("/api/run/template/{template_id}")
def run_template(template_id: str, body: TemplateRunRequest):
    tpl = load_template(template_id)
    full_prompt = tpl["system_prompt"] + "\n\n" + body.input_text
    result = AgentLoop().run_task(full_prompt, tpl["tokens"], tpl["level"])
    return result
```

New CLI subcommand:
```bash
python3 main.py run-template --template doc-summary --input-file contract.txt
```

**Why it works with no Core changes:** `AgentLoop.run_task()` already accepts any string as `prompt`.
Templates are pure configuration — adding one is just adding a JSON file.

### 9.2 Agent Integration

**What:** embed CostAgent into enterprise workflows so it becomes an internal AI endpoint.

| Integration | How it calls CostAgent | What enables it |
|---|---|---|
| **Slack bot** | Slack webhook → `POST /api/run/template/{id}` | stateless JSON API |
| **CRM trigger** | CRM event → HTTP call to API server | standard REST interface |
| **ERP / internal system** | Internal service → `POST /api/run` | pydantic schema is the contract |
| **CLI automation / cron** | `python3 main.py run-task --input-file data.txt --output-file out.json` | `--output-file` flag |
| **Multi-step agent chain** | Call `run_task()` N times, feed `result["response"]` as next prompt | dict return with `response` key |

**Key principle:** these integrations require **zero changes to Core**. The API server is already
a standard stateless REST service. The only additions needed are:
- A lightweight Slack event handler (`examples/slack_integration.py`)
- A webhook endpoint (`POST /api/webhook`)
- A `run-template` CLI subcommand

---

## 10. Upgrade Roadmap

| Version | Milestone | What to build | Enterprise value |
|---|---|---|---|
| **v0.1** | MVP | Core + CLI + API + logging | Working prototype, local cost estimation |
| **v0.1.1** | Real API calls | litellm integration, execute mode, Gemini test config | Actual LLM calls with cost tracking; estimated vs actual cost comparison |
| **v0.2** | Enterprise templates | `config/templates/*.json` + `/api/run/template/{id}` | Out-of-the-box task bundles; no prompt engineering needed |
| **v0.3** | Agent integration | Webhook endpoint + Slack example + multi-step chaining | Embed into enterprise workflows (Slack, CRM, ERP) |
| **v0.4** | Historical routing | Replace `route_task()` heuristic with model trained on `task_log.db` | Smarter routing based on real usage data |
| **v1.0** | Cloud + SLA | Docker + gunicorn, auth middleware, rate limiting | Production-ready deployment with uptime guarantees |
| **v1.x** | Advanced strategy subscription | Per-tenant config, usage analytics dashboard | Paid tier with ongoing optimization and insights |

### How each version builds on the previous:

```
v0.1 (MVP)
  └─ v0.2 (Templates)        ← templates call AgentLoop.run_task(), no Core changes
       └─ v0.3 (Integration)  ← integrations call /api/run/template/, no Core changes
            └─ v0.4 (Smart routing)  ← new ProbabilisticRouter reads from task_log.db
                 └─ v1.0 (Cloud)     ← Dockerize api_server.py, add auth middleware
                      └─ v1.x (Paid tier)  ← per-tenant config, analytics dashboard
```

---

## 11. Design Principles for Future Development

1. **Config over code** — adding a model or template should only require a JSON file change
2. **Core is sacred** — `AgentLoop.run_task()` is the single orchestration method; don't bypass it
3. **Memory is internal** — only AgentLoop reads/writes the database; CLI and API go through Core
4. **CLI is a thin client** — it calls the API via HTTP; it never imports Core or Memory
5. **Tests mock prices** — inject a fixture dict into constructors; never read from filesystem in tests
