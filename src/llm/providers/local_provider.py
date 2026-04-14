from __future__ import annotations

import hashlib

import numpy as np

from src.config.settings import settings
from src.llm.gateway import LlmHealth, LlmProvider, SemanticExtraction


class LocalProvider(LlmProvider):
    """
    本地模型 provider 占位实现。
    后续切换 vLLM/Ollama/自建推理服务时仅需替换本类实现。
    """

    def __init__(self) -> None:
        self.embedding_model = settings.local_embedding_model
        self.multimodal_model = settings.local_multimodal_model

    def _fallback_embedding(self, text: str, dim: int = 64) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        base = np.frombuffer(digest, dtype=np.uint8).astype(np.float32)
        repeated = np.resize(base, dim)
        norm = np.linalg.norm(repeated) or 1.0
        return repeated / norm

    def health(self) -> LlmHealth:
        return LlmHealth(
            ok=False,
            provider="local",
            embedding_model=self.embedding_model,
            multimodal_model=self.multimodal_model,
            detail="local provider is placeholder; implement inference backend first",
        )

    def extract_semantics(
        self,
        text: str,
        image_url: str | None = None,
        video_hint: str | None = None,
    ) -> SemanticExtraction:
        return SemanticExtraction(
            raw_description=f"[local_stub] {text[:120]}",
            topic="other",
            stance="neutral",
            emotion_score=3,
            summary=text[:120],
        )

    def embed_text_batch(self, texts: list[str]) -> np.ndarray:
        vectors = [self._fallback_embedding(text) for text in texts]
        return np.vstack(vectors)

    def embed_multimodal(self, text: str, image_url: str | None = None, video_frame: str | None = None) -> np.ndarray:
        merged_text = " ".join([x for x in [text, image_url or "", video_frame or ""] if x]).strip() or "empty_content"
        return self.embed_text_batch([merged_text])[0]
