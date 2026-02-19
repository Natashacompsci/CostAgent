import os
import threading
from pathlib import Path

from sqlite_utils import Database

# --- Database location & environment ---

# Allow overriding the DB path via env for multi-environment deployments.
# Default remains the original ./memory/task_log.db for backwards compatibility.
_DEFAULT_DB_PATH = Path(__file__).parent / "task_log.db"


def get_env_name() -> str:
    return os.getenv("ENV_NAME", "dev")


def get_db_path() -> Path:
    raw = os.getenv("TASK_LOG_DB_PATH")
    if raw:
        return Path(raw)
    return _DEFAULT_DB_PATH

_INIT_LOCK = threading.Lock()
_INIT_DONE = False
_DB_CACHE_LOCK = threading.Lock()
_DB_CACHE: dict[str, Database] = {}


# --- Schema for the task_runs table ---
#
# New fields are appended to support multi-environment analysis and
# richer metrics for routing / compression / latency.
_SCHEMA = {
    "id":                   int,
    "timestamp":            str,
    "env_name":             str,
    "trace_id":             str,
    "tenant_id":            str,
    "caller_id":            str,
    "model":                str,
    "task_level":           int,
    "status":               str,
    "error_type":           str,
    "error_message":        str,
    "prompt_tokens":        int,
    "output_tokens":        int,
    "prompt_cost":          float,
    "completion_cost":      float,
    "total_cost":           float,
    "budget":               float,
    "budget_exceeded":      int,   # 0 or 1 (SQLite has no boolean)
    "raw_prompt_len":       int,
    "compressed_prompt_len": int,
    "compression_ratio":    float,
    "latency_ms":           float,
    "router_reason":        str,
    "compressed_prompt":    str,
    "actual_cost":          float,
    "actual_output_tokens": int,
}


def get_db() -> Database:
    """Open (or create) the SQLite database at DB_PATH."""
    path = str(get_db_path())
    with _DB_CACHE_LOCK:
        db = _DB_CACHE.get(path)
        if db is None:
            db = Database(path)
            # Reduce lock flakiness under multi-threaded access (FastAPI/TestClient).
            db.conn.execute("PRAGMA busy_timeout = 5000")
            db.conn.execute("PRAGMA journal_mode = WAL")
            _DB_CACHE[path] = db
        return db


def init_db() -> None:
    """Create core tables if they do not exist and record schema version.

    Safe to call multiple times.
    """
    global _INIT_DONE
    if _INIT_DONE:
        return

    with _INIT_LOCK:
        if _INIT_DONE:
            return

        db = get_db()
        tables = db.table_names()

        if "task_runs" not in tables:
            db["task_runs"].create(_SCHEMA, pk="id")

        # Minimal meta table to track schema version for future migrations.
        if "meta" not in tables:
            db["meta"].create({"key": str, "value": str}, pk="key")
            db.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)",
                ["schema_version", "2"],
            )
        else:
            # Avoid writing on every init to reduce lock contention. Only insert
            # the schema_version row if it doesn't exist.
            row = db.execute(
                "SELECT value FROM meta WHERE key = ? LIMIT 1",
                ["schema_version"],
            ).fetchone()
            if row is None:
                db.execute(
                    "INSERT INTO meta (key, value) VALUES (?, ?)",
                    ["schema_version", "2"],
                )

        _INIT_DONE = True


def insert_run(run_data: dict) -> int:
    """Insert one task run record. Returns the new row id."""
    db = get_db()
    db["task_runs"].insert(run_data, alter=True)
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
    print("DB initialised at:", get_db_path())
    print("Tables:", get_db().table_names())
    print("Cumulative cost:", get_cumulative_cost())
