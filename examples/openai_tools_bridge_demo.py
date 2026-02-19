"""Demo: Use CostAgent as OpenAI-style tools.

This script does NOT call OpenAI. It shows how to:
1) expose CostAgent as tool schemas (function calling contract)
2) dispatch tool calls to CostAgent HTTP endpoints

Run:
  python3 examples/openai_tools_bridge_demo.py
"""

from integrations.openai_tools import dispatch, get_tools


def main() -> None:
    base_url = "http://localhost:8000"

    tools = get_tools()
    print("Tools to register with your agent framework:")
    for t in tools:
        fn = t["function"]
        print(f"- {fn['name']}: {fn['description']}")

    # Pretend an agent decided to call a tool:
    tool_name = "costagent_estimate"
    arguments = {"input_text": "Summarize the following text...", "level": 1, "tokens": 120}

    print("\nDispatching tool call to CostAgent:")
    print("tool_name =", tool_name)
    print("arguments =", arguments)

    result = dispatch(base_url=base_url, tool_name=tool_name, arguments=arguments)
    print("\nResult:")
    print(result)


if __name__ == "__main__":
    main()

