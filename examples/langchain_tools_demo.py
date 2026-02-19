"""Demo: Use CostAgent tools inside LangChain/LangGraph.

This example assumes you have installed:
  pip install langchain-core langchain-openai

It shows how to:
  - build LangChain StructuredTool objects from CostAgent
  - attach them to a ChatOpenAI model that supports tools

Run (with CostAgent API server running on localhost:8000):
  python3 examples/langchain_tools_demo.py
"""

from __future__ import annotations

from integrations.langchain_tools import get_langchain_tools


def main() -> None:
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise SystemExit(
            "langchain-openai is required for this demo. "
            "Install with: pip install langchain-openai"
        ) from exc

    tools = get_langchain_tools(
        base_url="http://localhost:8000",
        tenant_id="demo-tenant",
        caller_id="langchain-demo",
    )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(tools)

    print("Calling LLM with tools bound (the model may choose to call CostAgent tools):")
    resp = llm.invoke("Before answering, estimate the cost of summarizing a 200 token text.")
    print(resp)


if __name__ == "__main__":
    main()

