"""Lightweight LLM-as-judge quality evaluator using litellm.

Evaluates LLM responses on relevance, completeness, accuracy, and clarity.
Returns a score (1-10), reason, and evaluation cost. Designed to fail-open:
on any error, returns a passing score so the pipeline is never blocked.
"""

import json
import re

import litellm

from utils.observability import get_logger, log_event

DEFAULT_JUDGE_MODEL = "gemini/gemini-2.0-flash"

JUDGE_PROMPT_TEMPLATE = """\
You are a quality evaluator. Rate the following AI response on a scale of 1-10.

Criteria:
- Relevance: Does the response address the prompt?
- Completeness: Does it cover the key points?
- Accuracy: Is the information correct and coherent?
- Clarity: Is it well-written and easy to understand?

Prompt:
{prompt}

Response:
{response}

Reply with ONLY a JSON object: {{"score": <integer 1-10>, "reason": "<one sentence>"}}"""


class QualityEvaluator:
    """Evaluate LLM output quality using a cheap judge model."""

    def __init__(self, judge_model: str | None = None):
        self.judge_model = judge_model or DEFAULT_JUDGE_MODEL

    def evaluate(self, prompt: str, response: str) -> dict:
        """Return {"score": int, "reason": str, "eval_cost": float}."""
        ops = get_logger("costagent.quality")
        judge_prompt = JUDGE_PROMPT_TEMPLATE.format(
            prompt=prompt[:2000],
            response=response[:3000],
        )
        try:
            result = litellm.completion(
                model=self.judge_model,
                messages=[{"role": "user", "content": judge_prompt}],
                max_tokens=100,
            )
            raw = result.choices[0].message.content or ""
            eval_cost = litellm.completion_cost(completion_response=result)
            score, reason = self._parse_score(raw)
            log_event(ops, "quality_eval_done",
                      score=score, reason=reason, eval_cost=eval_cost)
            return {"score": score, "reason": reason, "eval_cost": eval_cost}
        except Exception as e:
            log_event(ops, "quality_eval_error", error=str(e))
            return {"score": 10, "reason": "eval_error: " + str(e)[:100], "eval_cost": 0.0}

    @staticmethod
    def _parse_score(raw: str) -> tuple[int, str]:
        """Extract score and reason from judge response. Fault-tolerant."""
        # Try JSON parse first
        try:
            data = json.loads(raw.strip())
            return int(data["score"]), data.get("reason", "")
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
        # Fallback: regex for score pattern
        match = re.search(r'"?score"?\s*[:=]\s*(\d+)', raw)
        if match:
            return min(int(match.group(1)), 10), raw.strip()[:100]
        # Last resort: fail-open
        return 10, "parse_error: " + raw.strip()[:100]
