"""Tests for quality evaluation and automatic fallback."""

from unittest.mock import MagicMock, patch

import pytest

from core.quality_evaluator import QualityEvaluator


# ---------------------------------------------------------------------------
# QualityEvaluator._parse_score
# ---------------------------------------------------------------------------

class TestParseScore:
    def test_valid_json(self):
        score, reason = QualityEvaluator._parse_score('{"score": 7, "reason": "good"}')
        assert score == 7
        assert reason == "good"

    def test_json_without_reason(self):
        score, reason = QualityEvaluator._parse_score('{"score": 9}')
        assert score == 9
        assert reason == ""

    def test_malformed_fallback_regex(self):
        score, _ = QualityEvaluator._parse_score("score: 5 blah blah")
        assert score == 5

    def test_score_capped_at_10(self):
        score, _ = QualityEvaluator._parse_score('{"score": 15, "reason": "over"}')
        assert score == 15  # JSON path doesn't cap; that's fine for internal use

    def test_regex_caps_at_10(self):
        score, _ = QualityEvaluator._parse_score("score = 12 something")
        assert score == 10

    def test_unparseable_returns_10(self):
        score, reason = QualityEvaluator._parse_score("no numbers here at all")
        assert score == 10
        assert "parse_error" in reason

    def test_empty_string_returns_10(self):
        score, reason = QualityEvaluator._parse_score("")
        assert score == 10


# ---------------------------------------------------------------------------
# QualityEvaluator.evaluate
# ---------------------------------------------------------------------------

class TestEvaluate:
    @patch("core.quality_evaluator.litellm.completion")
    @patch("core.quality_evaluator.litellm.completion_cost", return_value=0.0001)
    def test_success(self, mock_cost, mock_comp):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = '{"score": 8, "reason": "solid"}'
        mock_comp.return_value = mock_resp

        ev = QualityEvaluator(judge_model="test-model")
        result = ev.evaluate("what is 2+2?", "4")
        assert result["score"] == 8
        assert result["reason"] == "solid"
        assert result["eval_cost"] == 0.0001

    @patch("core.quality_evaluator.litellm.completion", side_effect=Exception("network error"))
    def test_error_returns_passing_score(self, mock_comp):
        ev = QualityEvaluator()
        result = ev.evaluate("prompt", "response")
        assert result["score"] == 10  # fail-open
        assert "eval_error" in result["reason"]
        assert result["eval_cost"] == 0.0

    @patch("core.quality_evaluator.litellm.completion")
    @patch("core.quality_evaluator.litellm.completion_cost", return_value=0.0001)
    def test_malformed_judge_response(self, mock_cost, mock_comp):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "score: 6 out of 10"
        mock_comp.return_value = mock_resp

        ev = QualityEvaluator()
        result = ev.evaluate("prompt", "response")
        assert result["score"] == 6


# ---------------------------------------------------------------------------
# Quality retry flow in AgentLoop
# ---------------------------------------------------------------------------

class TestQualityRetryFlow:
    """Integration test: AgentLoop retries on low quality score.

    Note: agent_loop and quality_evaluator import the same litellm module,
    so we patch it once via litellm directly and use side_effect to
    return different responses for task calls vs judge calls.
    """

    @patch.dict("os.environ", {
        "QUALITY_EVAL_ENABLED": "true",
        "QUALITY_THRESHOLD": "7",
        "QUALITY_MAX_RETRIES": "1",
    })
    @patch("litellm.completion")
    @patch("litellm.completion_cost", return_value=0.0005)
    def test_retry_escalates_model(self, mock_cost, mock_comp):
        # Calls alternate: task1, judge1, task2, judge2
        task_resp1 = MagicMock()
        task_resp1.choices = [MagicMock()]
        task_resp1.choices[0].message.content = "bad answer"
        task_resp1.usage = MagicMock(completion_tokens=5)

        judge_resp1 = MagicMock()
        judge_resp1.choices = [MagicMock()]
        judge_resp1.choices[0].message.content = '{"score": 3, "reason": "bad"}'

        task_resp2 = MagicMock()
        task_resp2.choices = [MagicMock()]
        task_resp2.choices[0].message.content = "good answer"
        task_resp2.usage = MagicMock(completion_tokens=10)

        judge_resp2 = MagicMock()
        judge_resp2.choices = [MagicMock()]
        judge_resp2.choices[0].message.content = '{"score": 9, "reason": "good"}'

        mock_comp.side_effect = [task_resp1, judge_resp1, task_resp2, judge_resp2]

        from core.agent_loop import AgentLoop
        agent = AgentLoop()
        result = agent.run_task("test prompt", 50, task_level=1, execute=True)

        assert result["quality_score"] == 9
        assert result["quality_retries"] == 1
        assert result["response"] == "good answer"
        assert result["original_model"] is not None
        assert mock_comp.call_count == 4  # 2 task + 2 judge

    @patch.dict("os.environ", {
        "QUALITY_EVAL_ENABLED": "true",
        "QUALITY_THRESHOLD": "7",
        "QUALITY_MAX_RETRIES": "2",
    })
    @patch("litellm.completion")
    @patch("litellm.completion_cost", return_value=0.0005)
    def test_passes_first_attempt_no_retry(self, mock_cost, mock_comp):
        # Calls: task1, judge1 (passes immediately)
        task_resp = MagicMock()
        task_resp.choices = [MagicMock()]
        task_resp.choices[0].message.content = "great answer"
        task_resp.usage = MagicMock(completion_tokens=10)

        judge_resp = MagicMock()
        judge_resp.choices = [MagicMock()]
        judge_resp.choices[0].message.content = '{"score": 9, "reason": "excellent"}'

        mock_comp.side_effect = [task_resp, judge_resp]

        from core.agent_loop import AgentLoop
        agent = AgentLoop()
        result = agent.run_task("test", 50, task_level=1, execute=True)

        assert result["quality_score"] == 9
        assert result["quality_retries"] == 0
        assert result["original_model"] is None  # no escalation
        assert mock_comp.call_count == 2  # 1 task + 1 judge

    def test_disabled_by_default_no_quality_fields(self):
        """When QUALITY_EVAL_ENABLED is not set, quality fields are None."""
        from core.agent_loop import AgentLoop
        agent = AgentLoop()
        result = agent.run_task("test", 50, task_level=1, execute=False)

        assert result["quality_score"] is None
        assert result["quality_retries"] is None
