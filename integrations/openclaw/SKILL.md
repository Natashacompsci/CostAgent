---
name: costagent
description: Cost-optimized LLM routing — estimate token costs, pick the cheapest model, enforce budgets before calling any LLM.
requires:
  env:
    - COSTAGENT_URL
  bins:
    - curl
    - jq
---

# CostAgent Skill

CostAgent is a cost-optimization layer for LLM calls. Use it to estimate costs, route to the cheapest suitable model, and enforce per-call budgets — all before spending real tokens.

## Estimate cost (read-only, no DB write)

When the user wants to know how much an LLM call will cost before making it:

```bash
curl -s -X POST "$COSTAGENT_URL/api/estimate" \
  -H "Content-Type: application/json" \
  -d "{\"input_text\": \"$PROMPT\", \"level\": $LEVEL, \"tokens\": $TOKENS}" | jq .
```

Parameters:
- `input_text` (required) — the prompt text
- `level` (1-3) — task complexity: 1=simple, 2=medium, 3=complex
- `tokens` — expected output token count

Returns: model, prompt_tokens, total_cost, budget_exceeded, compression_ratio

## Route to optimal model (read-only)

When the user wants to know which model CostAgent would pick:

```bash
curl -s -X POST "$COSTAGENT_URL/api/route" \
  -H "Content-Type: application/json" \
  -d "{\"level\": $LEVEL}" | jq .
```

Returns: model name and router_reason

## Run task (estimate + optional execution)

Full pipeline: compress prompt, route model, estimate cost, check budget, optionally call the LLM:

```bash
curl -s -X POST "$COSTAGENT_URL/api/run" \
  -H "Content-Type: application/json" \
  -d "{\"input_text\": \"$PROMPT\", \"level\": $LEVEL, \"tokens\": $TOKENS, \"execute\": $EXECUTE}" | jq .
```

- Set `execute` to `true` to actually call the LLM API
- Set `execute` to `false` (default) for a dry-run cost estimate only
- Optional: `budget` (float) to override per-call budget limit
- Optional: `model` (string) to override the router's model selection

## Check run history

```bash
curl -s "$COSTAGENT_URL/api/runs?limit=5" | jq .
```

## Error codes

When an error occurs, the response includes a structured `error_code`:
- `provider_unavailable` — LLM provider is down or rate-limited
- `provider_auth_error` — API key is invalid or missing
- `internal_error` — unexpected server error
