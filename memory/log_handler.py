import os
import uuid

from memory.db import get_cumulative_cost, get_env_name, init_db, insert_run
from utils.helpers import utc_now_iso


class LogHandler:
    """Adapter between AgentLoop's result dict and the SQLite database layer."""

    def __init__(self):
        init_db()   # idempotent; creates the table if it does not exist

    def log_run(self, run_result: dict, task_level: int) -> int:
        """
        Persist one task run to the database.

        Maps keys from AgentLoop.run_task()'s return dict to the db schema,
        adds a UTC timestamp and env name, and returns the inserted row id.
        """
        trace_id = run_result.get("trace_id") or str(uuid.uuid4())
        status = run_result.get("status", "unknown")
        router_reason = run_result.get("router_reason", "")

        raw_prompt_len = run_result.get("raw_prompt_len")
        compressed_prompt = run_result.get("compressed_prompt", "") or ""
        compressed_len = run_result.get("compressed_prompt_len")

        if raw_prompt_len is None and "compressed_prompt" in run_result:
            # Fall back to character lengths when not explicitly provided.
            raw_prompt_len = len(run_result.get("original_prompt", ""))
        if compressed_len is None:
            compressed_len = len(compressed_prompt)

        if raw_prompt_len and raw_prompt_len > 0:
            compression_ratio = compressed_len / raw_prompt_len
        else:
            compression_ratio = 1.0

        record = {
            "timestamp":             utc_now_iso(),
            "env_name":              os.getenv("ENV_NAME", get_env_name()),
            "trace_id":              trace_id,
            "tenant_id":             run_result.get("tenant_id"),
            "caller_id":             run_result.get("caller_id"),
            "model":                 run_result.get("model", "unknown"),
            "task_level":            task_level,
            "status":                status,
            "error_type":            run_result.get("error_type"),
            "error_message":         run_result.get("error_message"),
            "prompt_tokens":         run_result.get("prompt_tokens", 0),
            "output_tokens":         run_result.get("output_tokens", 0),
            "prompt_cost":           run_result.get("prompt_cost", 0.0),
            "completion_cost":       run_result.get("completion_cost", 0.0),
            "total_cost":            run_result.get("total_cost", 0.0),
            "budget":                run_result.get("budget"),
            "budget_exceeded":       int(run_result.get("budget_exceeded", False)),
            "raw_prompt_len":        raw_prompt_len or 0,
            "compressed_prompt_len": compressed_len,
            "compression_ratio":     compression_ratio,
            "latency_ms":            run_result.get("latency_ms"),
            "router_reason":         router_reason,
            "compressed_prompt":     compressed_prompt,
            "actual_cost":           run_result.get("actual_cost"),
            "actual_output_tokens":  run_result.get("actual_output_tokens"),
        }
        return insert_run(record)

    def cumulative_cost(self) -> float:
        """Return the sum of all total_cost values across all logged runs."""
        return get_cumulative_cost()


if __name__ == "__main__":
    handler = LogHandler()
    fake_result = {
        "model": "GPT-4o",
        "prompt_tokens": 10, "output_tokens": 50,
        "prompt_cost": 0.00005, "completion_cost": 0.00075, "total_cost": 0.0008,
        "budget_exceeded": False, "compressed_prompt": "test prompt",
    }
    row_id = handler.log_run(fake_result, task_level=2)
    print(f"Logged run with id={row_id}")
    print(f"Cumulative cost: ${handler.cumulative_cost():.5f}")
