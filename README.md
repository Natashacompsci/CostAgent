# CostAgent

Lightweight Token Cost Optimization & Model Routing Agent.

Estimates LLM API costs **before** making calls, routes tasks to the optimal model based on complexity,
compresses prompts to reduce token usage, and logs all runs for budget tracking. Supports dry-run
(estimation only) and execute mode (real API calls via [litellm](https://github.com/BerriAI/litellm)).

**Key differentiators:**
- **Cross-provider smart routing** — configure multiple API keys and CostAgent automatically picks the most cost-effective model for each task complexity level
- **Quality-aware auto-fallback** — optional LLM-as-judge quality gate that automatically retries with a stronger model when output quality is low, ensuring reliable results even with cheap models

## How It Works

```
Your App / Agent
       │
       ▼
  POST /api/run
       │
       ▼
┌─────────────────┐
│   CostAgent     │
│                 │
│  Compress       │
│  Route          │
│  Estimate       │
│  Budget-check   │
│  [Execute]      │
│  [Quality gate] │
│  Log            │
└────────┬────────┘
         │
         ▼
   Structured response
   (model, cost, budget_exceeded, response)
```

CostAgent takes your prompt, optimizes it, selects the best model, checks your budget, and optionally
calls the LLM — all through a single API call.

## Requirements

- Python 3.11+
- API key for at least one LLM provider

## Setup

```bash
git clone https://github.com/Natashacompsci/CostAgent.git
cd CostAgent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your API key(s):

```bash
cp .env.example .env
# Edit .env — only fill in the key(s) you have
```

## BYOK (Bring Your Own Key)

CostAgent uses [litellm](https://github.com/BerriAI/litellm) which reads API keys from environment
variables. Set the key(s) for the provider(s) you want to use:

| Provider | Env Variable | L1 (Simple) | L2 (Medium) | L3 (Complex) |
|----------|-------------|-------------|-------------|--------------|
| Google | `GOOGLE_API_KEY` | Gemini 2.0 Flash | Gemini 2.5 Flash | Gemini 2.5 Pro |
| OpenAI | `OPENAI_API_KEY` | GPT-4o Mini | GPT-4o | o3-mini |
| Anthropic | `ANTHROPIC_API_KEY` | Claude Haiku | Claude Sonnet | Claude Opus |
| DeepSeek | `DEEPSEEK_API_KEY` | DeepSeek V3 | _(fallback)_ | DeepSeek R1 |

### Routing Modes

| Mode | When | Behavior |
|------|------|----------|
| **Auto (mixed)** | Multiple API keys set | Picks best model per level across all providers |
| **Single provider** | One key set, or `PROVIDER=google` | Routes within that provider's models only |
| **Custom** | Edit `config/models_price.json` | Use any litellm-supported model |

**Auto mode example:** with both `GOOGLE_API_KEY` and `OPENAI_API_KEY`:
```
L1 → Gemini 2.0 Flash  (cheapest available)
L2 → GPT-4o            (best value mid-tier)
L3 → o3-mini           (strongest available)
```

To force a specific provider: `PROVIDER=openai` in `.env`.

## Usage

### Start the API server

```bash
python3 api_server.py
```

### CLI Commands

```bash
# Dry-run: estimate cost without calling the LLM (default)
python3 main.py run-task -p "What is the capital of France?" -t 20 -l 1

# Execute: make a real API call (costs money / uses free tier)
python3 main.py run-task -p "What is the capital of France?" -t 20 -l 1 -e

# Read prompt from file
python3 main.py run-task -f examples/test_doc.txt -t 200 -l 2

# Override model (bypass router)
python3 main.py run-task -p "Hello" -t 20 -l 1 -m "gpt-4o"

# Override budget
python3 main.py run-task -p "Hello" -t 20 -l 1 -b 0.05

# Save result to file
python3 main.py run-task -p "Hello" -t 20 -l 1 -o result.json

# View recent runs
python3 main.py history -n 5

# Check cumulative cost
python3 main.py budget-check

# Show current provider and model routing
python3 main.py providers
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--prompt` | `-p` | Inline prompt text |
| `--input-file` | `-f` | Read prompt from file |
| `--output-file` | `-o` | Save result JSON to file |
| `--tokens` | `-t` | Expected output tokens (default: 100) |
| `--level` | `-l` | Task complexity 1-3 (default: 1) |
| `--model` | `-m` | Override auto-routing |
| `--budget` | `-b` | Per-call budget override |
| `--execute` | `-e` | Actually call the LLM API |

## API

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/run` | POST | Full pipeline: estimate + optional execution + logging |
| `/api/estimate` | POST | Read-only cost estimate (no logging, no execution) |
| `/api/route` | POST | Model selection only |
| `/api/runs` | GET | Query run history |
| `/health` | GET | Health check |

### POST /api/run

Request:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| input_text | string | yes | - | The prompt |
| tenant_id | string | no | null | Tenant identifier for multi-agent attribution |
| caller_id | string | no | null | Caller/service identifier for attribution |
| level | int (1-3) | no | 1 | Task complexity |
| tokens | int | no | 100 | Expected output tokens |
| model | string | no | null | Override auto-routing |
| budget | float | no | null | Per-call budget override |
| execute | bool | no | false | True = call LLM API; False = dry-run |

Response (200):

| Field | Type | Description |
|-------|------|-------------|
| model | string | Model used |
| prompt_tokens | int | Prompt token count |
| total_cost | float | Estimated total cost |
| budget_exceeded | bool | Whether cost exceeds budget |
| cumulative_cost | float | Total cost across all runs |
| response | string | LLM response or dry-run message |
| actual_cost | float/null | Real cost (execute mode only) |
| quality_score | int/null | Quality score 1-10 (when quality eval enabled) |
| quality_retries | int/null | Number of model escalation retries |
| quality_eval_cost | float/null | Cost of quality evaluation calls |
| original_model | string/null | Original model before escalation (if retried) |
| summary | string | Formatted summary |
| trace_id | string | Correlation ID |

Error response (500/502):

| Field | Type | Description |
|-------|------|-------------|
| error_code | string | `provider_unavailable` / `provider_auth_error` / `internal_error` |
| message | string | Human-readable error description |
| trace_id | string/null | Correlation ID |
| details | object/null | Extra context (e.g. exception type) |

## Integrations

CostAgent can be integrated into any agent framework. See [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) for details.

| Method | Best for |
|--------|----------|
| HTTP API | Any language / framework |
| Python SDK | Python scripts, custom agents |
| OpenAI tools | GPT-based agents, AutoGen |
| LangChain tools | LangChain / LangGraph agents |
| OpenClaw Skill | OpenClaw personal AI assistant |

### Quick example (Python SDK)

```python
from costagent_sdk import CostAgentClient

client = CostAgentClient(tenant_id="my-app", caller_id="my-agent")
result = client.run(input_text="Summarize this article...", level=2, tokens=200)
print(f"Model: {result['model']}, Cost: ${result['total_cost']:.6f}")
```

## Model Configuration

### Option 1: Provider presets (recommended)

Set your API key(s) in `.env` and CostAgent auto-configures:

```bash
# .env
GOOGLE_API_KEY=your_key    # → auto-selects Google preset
OPENAI_API_KEY=your_key    # → if both set, auto mode kicks in
```

### Option 2: Explicit provider

```bash
# .env
PROVIDER=openai            # → force OpenAI preset regardless of other keys
```

### Option 3: Custom models

Edit `config/models_price.json` to define your own model pool:

```json
{
  "gpt-4o-mini":           { "display_name": "GPT-4o Mini",  "level": 1 },
  "gemini/gemini-2.5-flash": { "display_name": "Gemini 2.5 Flash", "level": 2 },
  "anthropic/claude-sonnet-4-20250514": { "display_name": "Claude Sonnet", "level": 3 }
}
```

Model IDs follow litellm's naming convention. Pricing is auto-fetched from litellm's built-in cost database.

**Priority:** `PROVIDER` env var > auto-detect from keys > `models_price.json` fallback.

## Environments & Observability

| Variable | Default | Purpose |
|---|---|---|
| `ENV_NAME` | `dev` | Tag runs with environment name (dev/staging/prod) |
| `TASK_LOG_DB_PATH` | `memory/task_log.db` | Override SQLite path (for Docker/production) |
| `LOG_LEVEL` | `INFO` | Log verbosity |
| `LOG_JSON` | `true` | Emit structured JSON logs to stdout |
| `QUALITY_EVAL_ENABLED` | `false` | Enable quality evaluation with auto-fallback |
| `QUALITY_THRESHOLD` | `6` | Minimum quality score (1-10) to accept without retry |
| `QUALITY_MAX_RETRIES` | `2` | Max escalation retries on low quality |
| `JUDGE_MODEL` | `gemini/gemini-2.0-flash` | Model used for quality evaluation |

Each run gets a `trace_id` for end-to-end correlation across logs and stored records.

## Test Tasks

See [examples/test_tasks.md](examples/test_tasks.md) for 70+ ready-to-run test commands.

## Running Tests

```bash
python3 -m pytest tests/ -v
```

## License

GPL-3.0 — see [LICENSE](LICENSE) for details.
