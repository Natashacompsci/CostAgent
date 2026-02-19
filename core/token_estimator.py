import litellm


class TokenEstimator:
    """Estimate LLM API cost using litellm for token counting and pricing."""

    def count_tokens(self, text: str, model_name: str) -> int:
        """Count tokens in text using litellm's tokenizer for the given model."""
        messages = [{"role": "user", "content": text}]
        return litellm.token_counter(model=model_name, messages=messages)

    def estimate(
        self,
        prompt_text: str,
        expected_output_tokens: int,
        model_name: str,
    ) -> dict:
        """
        Estimate cost for a prompt + expected output.

        Returns a dict with full cost breakdown:
          model, prompt_tokens, output_tokens,
          prompt_cost, completion_cost, total_cost
        """
        prompt_tokens = self.count_tokens(prompt_text, model_name)
        try:
            prompt_cost, completion_cost = litellm.cost_per_token(
                model=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=expected_output_tokens,
            )
        except (litellm.exceptions.NotFoundError, Exception):
            prompt_cost, completion_cost = 0.0, 0.0

        return {
            "model":           model_name,
            "prompt_tokens":   prompt_tokens,
            "output_tokens":   expected_output_tokens,
            "prompt_cost":     prompt_cost,
            "completion_cost": completion_cost,
            "total_cost":      prompt_cost + completion_cost,
        }


if __name__ == "__main__":
    estimator = TokenEstimator()
    result = estimator.estimate(
        prompt_text="Explain quantum computing in simple terms.",
        expected_output_tokens=200,
        model_name="gpt-4o",
    )
    for k, v in result.items():
        print(f"  {k}: {v}")
