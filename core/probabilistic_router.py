from config.config import get_model_prices


class ProbabilisticRouter:
    """Route tasks to different models based on complexity level."""

    def __init__(self, model_config: dict | None = None):
        self.model_config = model_config or get_model_prices()

    def route_task(self, task_level: int) -> str:
        """
        Return a litellm model ID based on task difficulty level.

        Looks up the model_config (from models_price.json) where each entry
        has a "level" field. Falls back to the highest-level model.
        """
        for model_id, info in self.model_config.items():
            if info.get("level") == task_level:
                return model_id
        # fallback to highest level model
        return max(
            self.model_config,
            key=lambda k: self.model_config[k].get("level", 0),
        )


if __name__ == "__main__":
    router = ProbabilisticRouter()
    for level in [1, 2, 3]:
        print(f"Level {level} -> {router.route_task(level)}")
