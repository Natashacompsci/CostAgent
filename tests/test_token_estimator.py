from unittest.mock import patch

import pytest

from core.token_estimator import TokenEstimator


@pytest.fixture
def estimator():
    return TokenEstimator()


@patch("core.token_estimator.litellm.token_counter", return_value=5)
@patch("core.token_estimator.litellm.cost_per_token", return_value=(0.0000025, 0.00001))
def test_estimate_returns_dict_with_required_keys(mock_cost, mock_counter):
    est = TokenEstimator()
    result = est.estimate("hello world", 50, "gpt-4o")
    required = {"model", "prompt_tokens", "output_tokens",
                "prompt_cost", "completion_cost", "total_cost"}
    assert required.issubset(result.keys())


@patch("core.token_estimator.litellm.token_counter", return_value=5)
@patch("core.token_estimator.litellm.cost_per_token", return_value=(0.0000025, 0.00001))
def test_estimate_total_is_sum_of_parts(mock_cost, mock_counter):
    est = TokenEstimator()
    result = est.estimate("hello world", 50, "gpt-4o")
    assert abs(result["total_cost"] - (result["prompt_cost"] + result["completion_cost"])) < 1e-10


@patch("core.token_estimator.litellm.token_counter", return_value=5)
@patch("core.token_estimator.litellm.cost_per_token", return_value=(0.0000125, 0.0005))
def test_estimate_cost_calculation(mock_cost, mock_counter):
    est = TokenEstimator()
    result = est.estimate("hello world", 50, "gpt-4o")
    assert result["prompt_tokens"] == 5
    assert result["output_tokens"] == 50
    assert result["prompt_cost"] == 0.0000125
    assert result["completion_cost"] == 0.0005


def test_count_tokens_returns_int(estimator):
    count = estimator.count_tokens("hello world", "gpt-4o")
    assert isinstance(count, int)
    assert count > 0


def test_count_tokens_empty_string(estimator):
    count = estimator.count_tokens("", "gpt-4o")
    assert isinstance(count, int)


def test_estimate_cost_scales_with_length(estimator):
    short = estimator.estimate("hi", 10, "gpt-4o")
    long_ = estimator.estimate("hi " * 500, 10, "gpt-4o")
    assert long_["prompt_cost"] > short["prompt_cost"]
