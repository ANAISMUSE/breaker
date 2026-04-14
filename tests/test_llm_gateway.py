from src.config.settings import settings
from src.llm import get_llm_provider


def test_local_provider_selection() -> None:
    settings.llm_provider = "local"
    provider = get_llm_provider()
    health = provider.health()
    assert health.provider == "local"
    assert health.ok is False


def test_dashscope_provider_selection() -> None:
    settings.llm_provider = "dashscope"
    provider = get_llm_provider()
    health = provider.health()
    assert health.provider == "dashscope"
    assert isinstance(health.ok, bool)
