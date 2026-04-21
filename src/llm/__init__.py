from __future__ import annotations

from src.config.settings import settings
from src.llm.gateway import LlmProvider
from src.llm.providers.dashscope_provider import DashScopeProvider
from src.llm.providers.local_provider import LocalProvider


def get_llm_provider() -> LlmProvider:
    mode = settings.inference_mode.strip().lower()
    provider = settings.llm_provider.strip().lower()
    if mode == "local" or provider == "local":
        return LocalProvider()
    return DashScopeProvider()
