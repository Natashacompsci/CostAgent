# CostAgent

Lightweight Token Cost Optimization & Model Routing Agent.

Estimates LLM API costs **before** making calls, routes tasks to the optimal model based on complexity,
compresses prompts to reduce token usage, and logs all runs for budget tracking. Supports dry-run
(estimation only) and execute mode (real API calls via [litellm](https://github.com/BerriAI/litellm)).

**Key differentiator:** cross-provider smart routing — configure multiple API keys and CostAgent
automatically picks the most cost-effective model for each task complexity level.

## Architecture

```
CLI (Typer) --> API Server (FastAPI) --> Core (AgentLoop) --> Memory (SQLite)
                                          |
                                    Config Layer
                              (providers.py + config.py)
                          auto-detect keys → build model pool
```

- **CLI** — thin httpx client, sends requests to the API server
- **API Server** — FastAPI, handles routing/estimation/execution
- **Core** — AgentLoop orchestrates: compress → route → estimate → budget-check → [execute] → log
- **Config** — auto-detects available API keys, builds optimal model pool across providers
- **Memory** — SQLite via sqlite-utils, stores per-run records for history and budget tracking
- **Observability** — structured logs to stdout (JSON by default) so you can hook into your logging stack

## Requirements

- Python 3.11+ (uses `X | Y` union syntax)
- API key for at least one LLM provider (see below)

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

CostAgent supports three routing modes:

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

### Environments & basic observability

CostAgent is designed to run in multiple environments (dev/staging/prod) and to integrate with your
existing logging pipeline:

- You can point the internal SQLite database to a custom path (e.g. a mounted volume in Docker).
- Each run is tagged with an environment name for easier separation of dev vs prod data.
- API and core components emit structured logs (JSON by default) with a correlation ID so you can
  trace a single call across your logging system.

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

# List all available provider presets
python3 main.py providers --list
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

## API Contract

### POST /api/run

Request:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| input_text | string | yes | - | The prompt |
| level | int (1-3) | no | 1 | Task complexity |
| tokens | int | no | 100 | Expected output tokens |
| model | string | no | null | Override auto-routing |
| budget | float | no | null | Per-call budget override |
| execute | bool | no | false | True = call LLM API; False = dry-run |

Response:

| Field | Type | Description |
|-------|------|-------------|
| model | string | Model used |
| prompt_tokens | int | Estimated prompt tokens |
| output_tokens | int | Expected output tokens |
| prompt_cost | float | Estimated prompt cost |
| completion_cost | float | Estimated completion cost |
| total_cost | float | Total estimated cost |
| budget | float | Budget used for this call |
| budget_exceeded | bool | Whether cost exceeds budget |
| cumulative_cost | float | Total cost across all runs |
| log_id | int | Database row ID |
| response | string | LLM response or dry-run message |
| actual_cost | float/null | Real cost (execute mode only) |
| actual_output_tokens | int/null | Real output tokens (execute mode only) |
| summary | string | Formatted summary text |

### GET /api/runs?limit=10

Returns `{"runs": [...]}` with the most recent runs.

### GET /health

Returns `{"status": "ok"}`.

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

## Test Tasks

See [examples/test_tasks.md](examples/test_tasks.md) for 70+ ready-to-run test commands covering
10 agent types, workflows, and edge cases.

## Running Tests

```bash
python3 -m pytest tests/ -v
```

## License

GPL-3.0 — see [LICENSE](LICENSE) for details.
