from datetime import datetime, timezone


def format_cost(cost: float, precision: int = 5) -> str:
    """Format a float cost as a dollar string, e.g. format_cost(0.00432) -> '$0.00432'."""
    return f"${cost:.{precision}f}"


def truncate_text(text: str, max_chars: int = 80, suffix: str = "...") -> str:
    """Truncate text to max_chars and append suffix if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - len(suffix)] + suffix


def build_run_summary(run_result: dict) -> str:
    """Build a formatted multi-line summary string from an AgentLoop result dict."""
    mode = "[Execute]" if run_result.get("actual_cost") is not None else "[Dry-run]"
    lines = [
        f"Mode:             {mode}",
        f"Model:            {run_result.get('model', 'unknown')}",
        f"Prompt tokens:    {run_result.get('prompt_tokens', 0)}",
        f"Output tokens:    {run_result.get('output_tokens', 0)}",
        f"Prompt cost:      {format_cost(run_result.get('prompt_cost', 0.0))}",
        f"Completion cost:  {format_cost(run_result.get('completion_cost', 0.0))}",
        f"Total cost (est): {format_cost(run_result.get('total_cost', 0.0))}",
        f"Budget:           {format_cost(run_result.get('budget', 0.0))}",
        f"Over budget:      {'Yes' if run_result.get('budget_exceeded') else 'No'}",
        f"Cumulative cost:  {format_cost(run_result.get('cumulative_cost', 0.0))}",
    ]
    if run_result.get("actual_cost") is not None:
        lines.append(f"Actual cost:      {format_cost(run_result['actual_cost'])}")
    if run_result.get("actual_output_tokens") is not None:
        lines.append(f"Actual tokens:    {run_result['actual_output_tokens']}")
    if "log_id" in run_result:
        lines.append(f"Log ID:           {run_result['log_id']}")
    response = run_result.get("response", "")
    if response and not response.startswith("[Dry-run]") and not response.startswith("[Budget exceeded]"):
        lines.append(f"\n--- Response ---\n{response}")
    return "\n".join(lines)


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    sample = {
        "model": "GPT-4o",
        "prompt_tokens": 42, "output_tokens": 100,
        "prompt_cost": 0.00021, "completion_cost": 0.0015, "total_cost": 0.00171,
        "budget": 1.0, "budget_exceeded": False,
        "cumulative_cost": 0.00342, "log_id": 7,
    }
    print(build_run_summary(sample))
    print("\nNow:", utc_now_iso())
