from memory.db import get_cumulative_cost, init_db, insert_run
from utils.helpers import utc_now_iso


class LogHandler:
    """Adapter between AgentLoop's result dict and the SQLite database layer."""

    def __init__(self):
        init_db()   # idempotent; creates the table if it does not exist

    def log_run(self, run_result: dict, task_level: int) -> int:
        """
        Persist one task run to the database.

        Maps keys from AgentLoop.run_task()'s return dict to the db schema,
        adds a UTC timestamp, and returns the inserted row id.
        """
        record = {
            "timestamp":        utc_now_iso(),
            "model":            run_result["model"],
            "task_level":       task_level,
            "prompt_tokens":    run_result["prompt_tokens"],
            "output_tokens":    run_result["output_tokens"],
            "prompt_cost":      run_result["prompt_cost"],
            "completion_cost":  run_result["completion_cost"],
            "total_cost":       run_result["total_cost"],
            "budget_exceeded":  int(run_result.get("budget_exceeded", False)),
            "compressed_prompt": run_result.get("compressed_prompt", ""),
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
