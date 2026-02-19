# CostAgent Test Tasks

Ready-to-run commands for testing CostAgent at each complexity level.
All commands assume the API server is running: `python3 api_server.py`

## Workflow

1. **Dry-run** first to see estimated cost (default, no `-e` flag)
2. Review the cost estimate
3. **Execute** with `-e` flag if cost is acceptable

---

## Level 1 — Simple (gemini-2.0-flash)

Short, factual answers. Cheapest model.

```bash
# One-line factual answer
python3 main.py run-task -p "What is the capital of France?" -t 20 -l 1

# Short translation
python3 main.py run-task -p "Translate 'hello world' to Spanish" -t 30 -l 1

# Simple math
python3 main.py run-task -p "What is 247 * 38?" -t 10 -l 1

# Execute mode (real API call)
python3 main.py run-task -p "What is the capital of France?" -t 20 -l 1 -e
```

## Level 2 — Medium (gemini-2.5-flash)

Multi-paragraph explanations, code generation, comparisons.

```bash
# Paragraph explanation
python3 main.py run-task -p "Explain how TCP/IP works in 3 paragraphs" -t 200 -l 2

# Code generation
python3 main.py run-task -p "Write a Python function to find all prime numbers up to n using the Sieve of Eratosthenes" -t 300 -l 2

# Comparison analysis
python3 main.py run-task -p "Compare REST vs GraphQL APIs: pros, cons, and when to use each" -t 400 -l 2

# Execute mode
python3 main.py run-task -p "Explain how TCP/IP works in 3 paragraphs" -t 200 -l 2 -e
```

## Level 3 — Complex (gemini-2.5-pro)

System design, deep analysis, long-form content. Most expensive model.

```bash
# System design
python3 main.py run-task -p "Design a microservices architecture for an e-commerce platform. Include service boundaries, communication patterns, data management strategy, and deployment considerations." -t 800 -l 3

# Deep trade-off analysis
python3 main.py run-task -p "Analyze the trade-offs between SQL and NoSQL databases for a social media application with 10M users. Consider read/write patterns, scaling, consistency, and cost." -t 600 -l 3

# Execute mode
python3 main.py run-task -p "Design a microservices architecture for an e-commerce platform" -t 800 -l 3 -e
```

## Budget Override

Test the budget guard — set a very low budget to trigger the "budget exceeded" response:

```bash
# This should trigger budget exceeded (budget = $0.00001)
python3 main.py run-task -p "Write a long essay about AI" -t 500 -l 3 -b 0.00001

# Normal budget
python3 main.py run-task -p "Write a long essay about AI" -t 500 -l 3 -b 1.0
```

## Model Override

Force a specific model regardless of level:

```bash
# Use level 3 model for a simple task
python3 main.py run-task -p "What is 2+2?" -t 10 -l 1 -m "gemini/gemini-2.5-pro"
```

## History & Budget Check

```bash
# View recent runs
python3 main.py history -n 10

# Check cumulative spend
python3 main.py budget-check
```

## API Calls (curl)

```bash
# Dry-run via API
curl -s -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"input_text": "What is the capital of France?", "tokens": 20, "level": 1}' | python3 -m json.tool

# Execute via API
curl -s -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"input_text": "What is the capital of France?", "tokens": 20, "level": 1, "execute": true}' | python3 -m json.tool

# List runs
curl -s http://localhost:8000/api/runs?limit=5 | python3 -m json.tool
```
