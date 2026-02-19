import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def _isolate_memory_db(tmp_path_factory: pytest.TempPathFactory):
    """Isolate SQLite DB per test session to avoid lock contention."""
    db_path = tmp_path_factory.mktemp("costagent") / "task_log_test.db"
    os.environ["TASK_LOG_DB_PATH"] = str(db_path)
    os.environ["ENV_NAME"] = "test"
    yield

