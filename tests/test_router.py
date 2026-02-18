import pytest

from core.probabilistic_router import ProbabilisticRouter

MOCK_CONFIG = {
    "deepseek/deepseek-chat": {"display_name": "DeepSeek-V3", "level": 1},
    "gpt-4o":                 {"display_name": "GPT-4o",      "level": 2},
    "anthropic/claude-sonnet-4-20250514": {"display_name": "Claude Sonnet 4", "level": 3},
}


@pytest.fixture
def router():
    return ProbabilisticRouter(model_config=MOCK_CONFIG)


def test_level_1_routes_to_deepseek(router):
    assert router.route_task(1) == "deepseek/deepseek-chat"


def test_level_2_routes_to_gpt4o(router):
    assert router.route_task(2) == "gpt-4o"


def test_level_3_routes_to_claude(router):
    assert router.route_task(3) == "anthropic/claude-sonnet-4-20250514"


def test_level_above_3_falls_back_to_highest(router):
    assert router.route_task(99) == "anthropic/claude-sonnet-4-20250514"


def test_routed_model_exists_in_config(router):
    for level in [1, 2, 3]:
        model = router.route_task(level)
        assert model in MOCK_CONFIG
