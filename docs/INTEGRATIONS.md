# CostAgent Integrations

CostAgent can be integrated into any agent framework or workflow via HTTP API, Python SDK, or framework-specific wrappers.

## Quick reference

| Method | Best for | File |
|--------|----------|------|
| HTTP API | Any language / framework | — |
| Python SDK | Python scripts, custom agents | `costagent_sdk.py` |
| OpenAI tools | GPT-based agents, AutoGen | `integrations/openai_tools.py` |
| LangChain tools | LangChain / LangGraph agents | `integrations/langchain_tools.py` |
| OpenClaw Skill | OpenClaw personal AI assistant | `integrations/openclaw/` |

---

## 1. HTTP API

Start the server:

```bash
python api_server.py
```

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/run` | POST | Full pipeline: compress + route + estimate + [execute] + log |
| `/api/estimate` | POST | Read-only cost estimate (no DB write, no execution) |
| `/api/route` | POST | Model selection only |
| `/api/runs` | GET | Query run history |
| `/health` | GET | Health check |

### Example: estimate cost

```bash
curl -s -X POST http://localhost:8000/api/estimate \
  -H "Content-Type: application/json" \
  -d '{"input_text": "Translate this to French: Hello world", "level": 1, "tokens": 50}' | jq .
```

### Example: run task

```bash
curl -s -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"input_text": "Summarize this article...", "level": 2, "tokens": 200, "execute": true}' | jq .
```

### Error responses

Error responses use a structured format with machine-readable `error_code`:

```json
{
  "error_code": "provider_unavailable",
  "message": "Connection refused",
  "trace_id": null,
  "details": {"exception_type": "APIConnectionError"}
}
```

Error codes: `provider_unavailable`, `provider_auth_error`, `internal_error`

---

## 2. Python SDK

```python
from costagent_sdk import CostAgentClient

client = CostAgentClient(
    base_url="http://localhost:8000",
    tenant_id="my-app",
    caller_id="summarizer-agent",
)

# Dry-run estimate
result = client.run(input_text="Hello world", level=1, tokens=50)
print(f"Cost: ${result['total_cost']:.6f}, Model: {result['model']}")

# Execute for real
result = client.run(input_text="Hello world", level=1, tokens=50, execute=True)
print(result["response"])
```

---

## 3. OpenAI tools (GPT agents, AutoGen)

```python
from integrations.openai_tools import get_tools, dispatch

# Register tools with your OpenAI-compatible agent
tools = get_tools()  # Returns 3 tool schemas: costagent_route, costagent_estimate, costagent_run

# When the agent calls a tool:
result = dispatch(
    base_url="http://localhost:8000",
    tool_name="costagent_estimate",
    arguments={"input_text": "Hello", "level": 1, "tokens": 50},
)
```

---

## 4. LangChain tools

```python
from integrations.langchain_tools import get_langchain_tools

tools = get_langchain_tools(
    base_url="http://localhost:8000",
    tenant_id="my-app",
    caller_id="langchain-agent",
)

# Use with any LangChain agent
from langchain.agents import initialize_agent
agent = initialize_agent(tools, llm, agent="structured-chat-zero-shot-react-description")
```

---

## 5. OpenClaw Skill

Copy the skill file to your OpenClaw installation:

```bash
mkdir -p ~/.openclaw/skills/costagent
cp integrations/openclaw/SKILL.md ~/.openclaw/skills/costagent/SKILL.md
export COSTAGENT_URL=http://localhost:8000
```

See [integrations/openclaw/README.md](../integrations/openclaw/README.md) for details.

---

## Multi-tenant attribution

All integration methods support `tenant_id` and `caller_id` for separating analytics by caller:

- **HTTP API**: Pass in request body
- **Python SDK**: Set on `CostAgentClient` constructor
- **LangChain**: Pass to `get_langchain_tools()`
- **OpenAI tools**: Include in tool arguments for `costagent_run`
