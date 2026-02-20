from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api_server import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_run_task_dry_run():
    r = client.post("/api/run", json={"input_text": "hello world", "tokens": 50, "level": 1})
    assert r.status_code == 200
    data = r.json()
    assert data["model"] == "gemini/gemini-2.0-flash"
    assert "total_cost" in data
    assert "cumulative_cost" in data
    assert "log_id" in data
    assert "summary" in data
    assert data["actual_cost"] is None
    assert "[Dry-run]" in data["response"]


def test_run_task_model_override():
    r = client.post("/api/run", json={
        "input_text": "hello world", "tokens": 50, "level": 1, "model": "gpt-4o"
    })
    assert r.status_code == 200
    assert r.json()["model"] == "gpt-4o"


def test_run_task_budget_override():
    r = client.post("/api/run", json={
        "input_text": "hello", "tokens": 50, "level": 2, "budget": 0.0001
    })
    assert r.status_code == 200
    data = r.json()
    assert data["budget"] == 0.0001


@patch("core.agent_loop.litellm.completion")
@patch("core.agent_loop.litellm.completion_cost", return_value=0.00042)
def test_run_task_execute_mode(mock_cost, mock_completion):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello from LLM!"
    mock_response.usage.completion_tokens = 8
    mock_completion.return_value = mock_response

    r = client.post("/api/run", json={
        "input_text": "hello", "tokens": 50, "level": 1, "execute": True
    })
    assert r.status_code == 200
    data = r.json()
    assert data["response"] == "Hello from LLM!"
    assert data["actual_cost"] == 0.00042
    mock_completion.assert_called_once()


def test_invalid_level_returns_422():
    r = client.post("/api/run", json={"input_text": "hi", "tokens": 50, "level": 4})
    assert r.status_code == 422


def test_missing_input_text_returns_422():
    r = client.post("/api/run", json={"tokens": 50, "level": 1})
    assert r.status_code == 422


def test_list_runs():
    # Ensure at least one run exists
    client.post("/api/run", json={"input_text": "test", "tokens": 10, "level": 1})
    r = client.get("/api/runs", params={"limit": 5})
    assert r.status_code == 200
    runs = r.json()["runs"]
    assert isinstance(runs, list)
    assert len(runs) >= 1


# --- Structured error response tests ---

@patch("core.agent_loop.litellm.completion", side_effect=Exception("Something went wrong"))
def test_run_error_returns_structured_error(mock_completion):
    r = client.post("/api/run", json={
        "input_text": "hello", "tokens": 50, "level": 1, "execute": True
    })
    assert r.status_code == 500
    data = r.json()
    assert data["error_code"] == "internal_error"
    assert "message" in data
    assert data["details"]["exception_type"] == "Exception"


@patch("core.agent_loop.litellm.completion", side_effect=type("AuthenticationError", (Exception,), {})("invalid api key"))
def test_run_auth_error_returns_502(mock_completion):
    r = client.post("/api/run", json={
        "input_text": "hello", "tokens": 50, "level": 1, "execute": True
    })
    assert r.status_code == 502
    data = r.json()
    assert data["error_code"] == "provider_auth_error"


@patch("core.agent_loop.litellm.completion", side_effect=type("APIConnectionError", (Exception,), {})("connection refused"))
def test_run_provider_error_returns_502(mock_completion):
    r = client.post("/api/run", json={
        "input_text": "hello", "tokens": 50, "level": 1, "execute": True
    })
    assert r.status_code == 502
    data = r.json()
    assert data["error_code"] == "provider_unavailable"
