from __future__ import annotations

from typing import Iterable

import numpy as np

from src.llm import get_llm_provider
from src.llm.gateway import SemanticExtraction


class DashScopeClient:
    """
    历史兼容适配器。实际调用由 LLM provider 决定：
    - dashscope (默认)
    - local (占位，后续替换推理后端)
    """

    def __init__(self) -> None:
        self.provider = get_llm_provider()

    def embed_text_batch(self, texts: Iterable[str]) -> np.ndarray:
        return self.provider.embed_text_batch([str(t) for t in texts])

    def describe_multimodal_content(self, text: str, image_url: str | None = None, video_hint: str | None = None) -> str:
        extraction = self.provider.extract_semantics(text=text, image_url=image_url, video_hint=video_hint)
        return extraction.raw_description

    def parse_structured_description(self, raw_text: str) -> dict:
        # 兼容旧调用：若需要结构化字段，优先走 extraction，
        # 解析失败则退回稳态默认值。
        try:
            extraction: SemanticExtraction = self.provider.extract_semantics(text=raw_text)
            return {
                "topic": extraction.topic,
                "stance": extraction.stance,
                "emotion_score": extraction.emotion_score,
                "summary": extraction.summary,
            }
        except Exception:
            return {
                "topic": "other",
                "stance": "neutral",
                "emotion_score": 3,
                "summary": raw_text[:200] if raw_text else "",
            }

    def embed_multimodal(self, text: str, image_url: str | None = None, video_frame: str | None = None) -> np.ndarray:
        return self.provider.embed_multimodal(text=text, image_url=image_url, video_frame=video_frame)
