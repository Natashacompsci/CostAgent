# CostAgent

Lightweight Token Cost Optimization & Model Routing Agent.

Estimates LLM API costs **before** making calls, routes tasks to the optimal model based on complexity,
compresses prompts to reduce token usage, and logs all runs for budget tracking. Supports dry-run
(estimation only) and execute mode (real API calls via [litellm](https://github.com/BerriAI/litellm)).

## Architecture

```
CLI (Typer) --> API Server (FastAPI) --> Core (AgentLoop) --> Memory (SQLite)
```

- **CLI** — thin httpx client, sends requests to the API server
- **API Server** — FastAPI, handles routing/estimation/execution
- **Core** — AgentLoop orchestrates: compress → route → estimate → budget-check → [execute] → log
- **Memory** — SQLite via sqlite-utils, tracks all runs and cumulative cost

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

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
# Edit .env with your keys
```

## BYOK (Bring Your Own Key)

CostAgent uses [litellm](https://github.com/BerriAI/litellm) which reads API keys from environment
variables. Set the key(s) for the provider(s) you want to use:

| Provider | Env Variable | Models |
|----------|-------------|--------|
| Google | `GOOGLE_API_KEY` | gemini-2.0-flash, gemini-2.5-flash, gemini-2.5-pro |
| OpenAI | `OPENAI_API_KEY` | gpt-4o, gpt-4o-mini, etc. |
| Anthropic | `ANTHROPIC_API_KEY` | claude-sonnet, claude-opus, etc. |

You only need the key for the models configured in `config/models_price.json`. By default,
CostAgent is configured with Gemini models (Google offers a free tier).

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
python3 main.py run-task -p "Hello" -t 20 -l 1 -m "gemini/gemini-2.5-pro"

# Override budget
python3 main.py run-task -p "Hello" -t 20 -l 1 -b 0.05

# Save result to file
python3 main.py run-task -p "Hello" -t 20 -l 1 -o result.json

# View recent runs
python3 main.py history -n 5

# Check cumulative cost
python3 main.py budget-check
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

Edit `config/models_price.json` to configure which model handles each complexity level:

```json
{
  "gemini/gemini-2.0-flash": { "display_name": "Gemini 2.0 Flash", "level": 1 },
  "gemini/gemini-2.5-flash": { "display_name": "Gemini 2.5 Flash", "level": 2 },
  "gemini/gemini-2.5-pro":   { "display_name": "Gemini 2.5 Pro",   "level": 3 }
}
```

Model IDs follow litellm's naming convention (`provider/model-name`). Pricing is auto-fetched
from litellm's built-in cost database.

## Test Tasks

See [examples/test_tasks.md](examples/test_tasks.md) for ready-to-run commands at each level.

## Running Tests

```bash
python3 -m pytest tests/ -v
```

## License

GPL-3.0 — see [LICENSE](LICENSE) for details.
