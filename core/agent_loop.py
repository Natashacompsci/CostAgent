import litellm

from config.config import get_budget, get_model_prices
from core.probabilistic_router import ProbabilisticRouter
from core.semantic_compressor import SemanticCompressor
from core.token_estimator import TokenEstimator
from memory.log_handler import LogHandler


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
        effective_budget = budget_override if budget_override is not None else self.budget

        # 1. Compress
        compressed = self.compressor.compress(prompt)

        # 2. Route (or override)
        model_name = model_override or self.router.route_task(task_level)

        # 3. Estimate cost
        estimate = self.estimator.estimate(compressed, expected_output_tokens, model_name)

        # 4. Budget check
        budget_exceeded = estimate["total_cost"] > effective_budget

        # 5. Build result
        result = {
            **estimate,
            "compressed_prompt": compressed,
            "budget_exceeded":   budget_exceeded,
            "budget":            effective_budget,
        }

        # 6. Execute or dry-run
        if execute and not budget_exceeded:
            response = litellm.completion(
                model=model_name,
                messages=[{"role": "user", "content": compressed}],
                max_tokens=expected_output_tokens,
            )
            result["response"] = response.choices[0].message.content
            result["actual_cost"] = litellm.completion_cost(completion_response=response)
        else:
            if budget_exceeded:
                result["response"] = f"[Budget exceeded] Would use {model_name}"
            elif execute:
                result["response"] = f"[Dry-run] Would use {model_name}"
            else:
                result["response"] = f"[Dry-run] Would use {model_name}"
            result["actual_cost"] = None

        # 7. Log to Memory
        row_id = self.logger.log_run(result, task_level)
        result["log_id"] = row_id

        # 8. Self-feedback: cumulative cost across all sessions
        cumulative = self.logger.cumulative_cost()
        result["cumulative_cost"] = cumulative

        if budget_exceeded:
            print(
                f"WARNING: task cost ${estimate['total_cost']:.5f} "
                f"exceeds per-task budget ${effective_budget:.5f}"
            )

        return result


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
