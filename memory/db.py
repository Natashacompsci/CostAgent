from pathlib import Path

from sqlite_utils import Database

DB_PATH = Path(__file__).parent / "task_log.db"

_SCHEMA = {
    "id":               int,
    "timestamp":        str,
    "model":            str,
    "task_level":       int,
    "prompt_tokens":    int,
    "output_tokens":    int,
    "prompt_cost":      float,
    "completion_cost":  float,
    "total_cost":       float,
    "budget_exceeded":  int,   # 0 or 1 (SQLite has no boolean)
    "compressed_prompt": str,
}


def get_db() -> Database:
    """Open (or create) the SQLite database at DB_PATH."""
    return Database(DB_PATH)


def init_db() -> None:
    """Create the task_runs table if it does not exist. Safe to call multiple times."""
    db = get_db()
    if "task_runs" not in db.table_names():
        db["task_runs"].create(_SCHEMA, pk="id")


def insert_run(run_data: dict) -> int:
    """Insert one task run record. Returns the new row id."""
    db = get_db()
    db["task_runs"].insert(run_data)
    return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_recent_runs(limit: int = 10) -> list[dict]:
    """Return the most recent `limit` runs as a list of dicts, newest first."""
    return list(get_db()["task_runs"].rows_where(order_by="-id", limit=limit))


def get_cumulative_cost() -> float:
    """Sum of all total_cost values across all logged runs (used by self-feedback)."""
    row = get_db().execute(
        "SELECT COALESCE(SUM(total_cost), 0.0) FROM task_runs"
    ).fetchone()
    return float(row[0])


if __name__ == "__main__":
    init_db()
    print("DB initialised at:", DB_PATH)
    print("Tables:", get_db().table_names())
    print("Cumulative cost:", get_cumulative_cost())
