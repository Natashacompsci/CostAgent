import time
import uuid

import litellm

from config.config import (
    get_budget,
    get_judge_model,
    get_model_prices,
    get_quality_eval_enabled,
    get_quality_max_retries,
    get_quality_threshold,
)
from core.probabilistic_router import ProbabilisticRouter
from core.quality_evaluator import QualityEvaluator
from core.semantic_compressor import SemanticCompressor
from core.token_estimator import TokenEstimator
from memory.log_handler import LogHandler
from utils.observability import get_logger, log_event


class AgentLoop:
    """
    Orchestrator: compress -> route -> estimate -> budget-check -> [execute] -> log.

    Integrates Memory via LogHandler for self-feedback (cumulative cost tracking).
    Supports two modes:
      - Dry-run (default): estimate cost without calling any LLM API
      - Execute: actually call the LLM via litellm and return a real response
    """

    def __init__(
        self,
        model_prices: dict | None = None,
        budget: float | None = None,
    ):
        prices = model_prices or get_model_prices()
        self.budget = budget if budget is not None else get_budget()
        self.estimator = TokenEstimator()
        self.compressor = SemanticCompressor()
        self.router = ProbabilisticRouter(prices)
        self.logger = LogHandler()
        self.quality_eval_enabled = get_quality_eval_enabled()
        self.quality_threshold = get_quality_threshold()
        self.quality_max_retries = get_quality_max_retries()
        if self.quality_eval_enabled:
            self.evaluator = QualityEvaluator(judge_model=get_judge_model())

    def run_task(
        self,
        prompt: str,
        expected_output_tokens: int,
        task_level: int,
        model_override: str | None = None,
        budget_override: float | None = None,
        execute: bool = False,
    ) -> dict:
        """
        Run the full agent pipeline and return a result dict.

        If execute=True, actually calls the LLM API via litellm.
        If execute=False (default), returns a dry-run estimate only.
        """
        ops = get_logger("costagent.ops")
        effective_budget = budget_override if budget_override is not None else self.budget
        trace_id = str(uuid.uuid4())
        t_start = time.perf_counter()

        log_event(
            ops,
            "run_start",
            trace_id=trace_id,
            task_level=task_level,
            execute=execute,
            expected_output_tokens=expected_output_tokens,
            model_override=model_override,
            budget=effective_budget,
        )

        try:
            # 1. Compress
            compressed = self.compressor.compress(prompt)
            log_event(
                ops,
                "compress_done",
                trace_id=trace_id,
                raw_prompt_len=len(prompt),
                compressed_prompt_len=len(compressed),
            )

            # 2. Route (or override)
            model_name = model_override or self.router.route_task(task_level)
            if model_override:
                router_reason = f"override:{model_override}"
            else:
                router_reason = f"router:level={task_level}"
            log_event(
                ops,
                "route_done",
                trace_id=trace_id,
                model=model_name,
                router_reason=router_reason,
            )

            # 3. Estimate cost
            estimate = self.estimator.estimate(compressed, expected_output_tokens, model_name)

            # 4. Budget check
            budget_exceeded = estimate["total_cost"] > effective_budget

            # 5. Build result
            result = {
                **estimate,
                "compressed_prompt":  compressed,
                "budget_exceeded":    budget_exceeded,
                "budget":             effective_budget,
                "trace_id":           trace_id,
                "router_reason":      router_reason,
                "raw_prompt_len":     len(prompt),
                "compressed_prompt_len": len(compressed),
                "compression_ratio":  (len(compressed) / len(prompt)) if prompt else 1.0,
            }

            # 6. Execute or dry-run
            if execute and not budget_exceeded:
                current_level = task_level
                current_model = model_name
                quality_score = None
                quality_reason = None
                quality_retries = 0
                total_eval_cost = 0.0
                original_model = model_name
                max_attempts = (1 + self.quality_max_retries) if self.quality_eval_enabled else 1

                for _attempt in range(max_attempts):
                    response = litellm.completion(
                        model=current_model,
                        messages=[{"role": "user", "content": compressed}],
                        max_tokens=expected_output_tokens,
                    )
                    raw_content = response.choices[0].message.content or ""
                    actual_cost = litellm.completion_cost(completion_response=response)
                    usage = response.usage

                    if self.quality_eval_enabled:
                        eval_result = self.evaluator.evaluate(compressed, raw_content)
                        quality_score = eval_result["score"]
                        quality_reason = eval_result["reason"]
                        total_eval_cost += eval_result["eval_cost"]

                        if quality_score >= self.quality_threshold:
                            break

                        if current_level < 3:
                            quality_retries += 1
                            current_level += 1
                            current_model = model_override or self.router.route_task(current_level)
                            log_event(ops, "quality_retry",
                                      trace_id=trace_id, score=quality_score,
                                      from_model=original_model, to_model=current_model,
                                      retry=quality_retries)
                            continue
                        else:
                            break  # already at L3, accept
                    else:
                        break  # no eval, single pass

                if raw_content.strip():
                    result["response"] = raw_content
                else:
                    result["response"] = "[Empty response] Model returned no content. Try increasing --tokens or rephrasing."
                result["actual_cost"] = actual_cost
                result["model"] = current_model
                if usage:
                    result["actual_output_tokens"] = usage.completion_tokens
                result["quality_score"] = quality_score
                result["quality_reason"] = quality_reason
                result["quality_retries"] = quality_retries
                result["quality_eval_cost"] = total_eval_cost
                result["original_model"] = original_model if quality_retries > 0 else None
                status = "executed"
            else:
                if budget_exceeded:
                    result["response"] = f"[Budget exceeded] Would use {model_name}"
                    status = "rejected_budget"
                else:
                    result["response"] = f"[Dry-run] Would use {model_name}"
                    status = "dry_run"
                result["actual_cost"] = None
                result["actual_output_tokens"] = None
                result["quality_score"] = None
                result["quality_reason"] = None
                result["quality_retries"] = None
                result["quality_eval_cost"] = None
                result["original_model"] = None

            t_end = time.perf_counter()
            result["latency_ms"] = (t_end - t_start) * 1000.0
            result["status"] = status

            # 7. Log to Memory
            row_id = self.logger.log_run(result, task_level)
            result["log_id"] = row_id

            # 8. Self-feedback: cumulative cost across all sessions
            result["cumulative_cost"] = self.logger.cumulative_cost()

            log_event(
                ops,
                "run_end",
                trace_id=trace_id,
                status=status,
                model=result.get("model"),
                total_cost=result.get("total_cost"),
                budget_exceeded=budget_exceeded,
                latency_ms=result.get("latency_ms"),
                log_id=result.get("log_id"),
            )

            if budget_exceeded:
                log_event(
                    ops,
                    "budget_exceeded",
                    trace_id=trace_id,
                    total_cost=result.get("total_cost"),
                    budget=effective_budget,
                )

            return result
        except Exception as e:
            t_end = time.perf_counter()
            latency_ms = (t_end - t_start) * 1000.0
            err_msg = str(e).split("\n")[0] if str(e) else repr(e)
            err_type = type(e).__name__

            ops.exception(
                "run_error",
                extra={"extra_fields": {"event": "run_error", "trace_id": trace_id, "error_type": err_type}},
            )

            # Persist a minimal error record to business Memory (no stack trace).
            try:
                error_result = {
                    "model": "unknown",
                    "prompt_tokens": 0,
                    "output_tokens": expected_output_tokens,
                    "prompt_cost": 0.0,
                    "completion_cost": 0.0,
                    "total_cost": 0.0,
                    "budget": effective_budget,
                    "budget_exceeded": False,
                    "compressed_prompt": "",
                    "actual_cost": None,
                    "actual_output_tokens": None,
                    "trace_id": trace_id,
                    "router_reason": "",
                    "raw_prompt_len": len(prompt),
                    "compressed_prompt_len": 0,
                    "compression_ratio": 1.0,
                    "latency_ms": latency_ms,
                    "status": "error",
                    "error_type": err_type,
                    "error_message": err_msg,
                    "response": "[Error] See operational logs for stack trace.",
                }
                row_id = self.logger.log_run(error_result, task_level)
                error_result["log_id"] = row_id
                error_result["cumulative_cost"] = self.logger.cumulative_cost()
            except Exception:
                # If logging fails, still re-raise the original exception.
                pass

            raise


if __name__ == "__main__":
    agent = AgentLoop()
    prompt = "Summarize the key points of this text for me"
    for level in [1, 2, 3]:
        result = agent.run_task(prompt, expected_output_tokens=200, task_level=level)
        print(f"\n--- Level {level} ---")
        print(f"  Model:       {result['model']}")
        print(f"  Tokens:      {result['prompt_tokens']} prompt + {result['output_tokens']} output")
        print(f"  Total cost:  ${result['total_cost']:.5f}")
        print(f"  Cumulative:  ${result['cumulative_cost']:.5f}")
        print(f"  Log ID:      {result['log_id']}")
