from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass
class LlmHealth:
    ok: bool
    provider: str
    embedding_model: str
    multimodal_model: str
    detail: str = ""


@dataclass
class SemanticExtraction:
    raw_description: str
    topic: str
    stance: str
    emotion_score: int
    summary: str


class LlmProvider(Protocol):
    def health(self) -> LlmHealth:
        ...

    def extract_semantics(
        self,
        text: str,
        image_url: str | None = None,
        video_hint: str | None = None,
    ) -> SemanticExtraction:
        ...

    def embed_text_batch(self, texts: list[str]) -> np.ndarray:
        ...

    def embed_multimodal(
        self,
        text: str,
        image_url: str | None = None,
        video_frame: str | None = None,
    ) -> np.ndarray:
        ...
