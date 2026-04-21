from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Protocol

import numpy as np


@dataclass
class LlmHealth:
    ok: bool
    provider: str
    inference_mode: str
    embedding_model: str
    multimodal_model: str
    report_model: str = ""
    capabilities: list[str] | None = None
    detail: str = ""


@dataclass
class SemanticExtraction:
    raw_description: str
    topic: str
    stance: str
    emotion_score: int
    summary: str


@dataclass
class MultimodalParseResult:
    text: str
    frame_summary: str
    audio_transcript: str
    subtitle_summary: str
    bullet_comments_summary: str
    normalized_description: str


@dataclass
class StrategyPlanResult:
    level: str
    topic: str
    reason: str
    confidence: float


@dataclass
class TrainingReviewResult:
    score: float
    feedback: str
    evidence: list[str]


@dataclass
class LlmInvokeResult:
    content: str
    usage: dict[str, int | float | str]
    raw: dict | list | None
    model: str
    finish_reason: str
    parsed_json: dict | list | None = None


def extract_json_payload(raw_text: str) -> dict | list | None:
    candidate = (raw_text or "").strip()
    if not candidate:
        return None
    if "```" in candidate:
        blocks = re.findall(r"```(?:json)?\s*(.*?)```", candidate, flags=re.S)
        if blocks:
            candidate = blocks[0].strip()
    try:
        return json.loads(candidate)
    except Exception:
        pass
    start_obj = candidate.find("{")
    end_obj = candidate.rfind("}")
    if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
        try:
            return json.loads(candidate[start_obj : end_obj + 1])
        except Exception:
            pass
    start_arr = candidate.find("[")
    end_arr = candidate.rfind("]")
    if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
        try:
            return json.loads(candidate[start_arr : end_arr + 1])
        except Exception:
            pass
    return None


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

    def parse_multimodal_context(
        self,
        *,
        text: str,
        video_hint: str | None = None,
        subtitles: list[str] | None = None,
        bullet_comments: list[str] | None = None,
    ) -> MultimodalParseResult:
        ...

    def generate_strategy_plan(
        self,
        *,
        blindspots: list[str],
        top_topics: list[str],
        history_notes: list[str],
    ) -> list[StrategyPlanResult]:
        ...

    def review_training_submission(
        self,
        *,
        topic: str,
        pro_view: str,
        con_view: str,
        summary: str,
        reflection: str,
    ) -> TrainingReviewResult:
        ...

    def invoke_text(self, *, prompt: str, model: str | None = None, temperature: float = 0.2) -> LlmInvokeResult:
        ...

    def invoke_json(
        self,
        *,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        retry_on_parse_error: bool = True,
    ) -> LlmInvokeResult:
        ...

    def invoke_multimodal(
        self,
        *,
        prompt: str,
        image_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> LlmInvokeResult:
        ...
