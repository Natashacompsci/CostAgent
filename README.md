# CostAgent

Lightweight Token Cost Optimization & Model Routing Agent.

Estimates LLM API costs before making calls, routes tasks to the optimal model based on complexity,
compresses prompts to reduce token usage, and logs all runs for budget tracking.

## Architecture

```
CLI (Typer) --> API Server (FastAPI) --> Core (AgentLoop) --> Memory (SQLite)
```

See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for full architecture details and upgrade roadmap.

## Setup

```bash
git clone <repo-url> && cd CostAgent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy `.env` and fill in your API keys:
```
OPENAI_API_KEY=your_key_here
CLAUDE_API_KEY=your_key_here
BUDGET_PER_CALL=1.0
```

## Usage

### Start the API server

```bash
python3 api_server.py
```

### CLI commands

```bash
# Basic task routing and cost estimation
python3 main.py run-task --prompt "Summarize this document" --tokens 200 --level 2

# Read prompt from file, override model, save result
python3 main.py run-task --input-file examples/test_doc.txt --model GPT-4o --output-file result.json

# Override budget
python3 main.py run-task --prompt "Translate this" --budget 0.05 --level 1

# View recent runs
python3 main.py history --limit 5

# Check cumulative cost
python3 main.py budget-check
```

### Direct API calls

```bash
# Run a task
curl -X POST http://localhost:8000/api/run \
     -H "Content-Type: application/json" \
     -d '{"input_text": "Explain quantum computing", "tokens": 150, "level": 3}'

# View recent runs
curl http://localhost:8000/api/runs?limit=5

# Health check
curl http://localhost:8000/health
```

### Standalone core test

```bash
python3 -m core.agent_loop
```

## API Contract

### POST /api/run

Request:
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| input_text | string | yes | - | The prompt |
| level | int (1-3) | no | 1 | Task complexity |
| tokens | int | no | 100 | Expected output tokens |
| model | string | no | null | Override auto-routing |
| budget | float | no | null | Per-call budget override |

Response includes: `model`, `prompt_tokens`, `output_tokens`, `prompt_cost`, `completion_cost`,
`total_cost`, `budget`, `budget_exceeded`, `cumulative_cost`, `log_id`, `response`, `summary`

## Running Tests

```bash
python3 -m pytest tests/ -v
```

## Model Pricing

Edit `config/models_price.json` to add or update model pricing. Each entry needs:
- `prompt_price_per_1k` — cost per 1,000 prompt tokens
- `completion_price_per_1k` — cost per 1,000 completion tokens
- `tiktoken_model` — tiktoken encoding to use for token counting
