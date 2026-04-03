from __future__ import annotations

import hashlib
import json
import re
from typing import Iterable

import numpy as np
import requests

from src.config.settings import settings


class DashScopeClient:
    def __init__(self) -> None:
        self.api_key = settings.dashscope_api_key
        self.base_url = settings.dashscope_base_url.rstrip("/")

    def _fallback_embedding(self, text: str, dim: int = 64) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        base = np.frombuffer(digest, dtype=np.uint8).astype(np.float32)
        repeated = np.resize(base, dim)
        norm = np.linalg.norm(repeated) or 1.0
        return repeated / norm

    def embed_text_batch(self, texts: Iterable[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            if not self.api_key:
                vectors.append(self._fallback_embedding(text))
                continue
            try:
                response = requests.post(
                    f"{self.base_url}/compatible-mode/v1/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": settings.embedding_model, "input": text},
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
                vectors.append(np.array(payload["data"][0]["embedding"], dtype=np.float32))
            except Exception:
                vectors.append(self._fallback_embedding(text))
        return np.vstack(vectors)

    def describe_multimodal_content(
        self, text: str, image_url: str | None = None, video_hint: str | None = None
    ) -> str:
        """
        Stage-1: Qwen2.5-Omni (or compatible multimodal chat model) generates
        a structured natural-language description.
        """
        merged_hint = " ".join([x for x in [text, video_hint or ""] if x]).strip()
        if not self.api_key:
            return f"[fallback_description] {merged_hint or 'empty_content'}"
        try:
            content = [
                {
                    "type": "text",
                    "text": (
                        "你是内容理解引擎。请严格返回JSON对象，不要输出多余文本。"
                        "字段: topic(英文小写), stance(left|center|right|neutral), "
                        "emotion_score(1-5整数), summary(中文简述)。"
                        f"\n待分析内容:\n{merged_hint}"
                    ),
                }
            ]
            if image_url:
                content.append({"type": "image_url", "image_url": {"url": image_url}})
            payload = {
                "model": settings.multimodal_model,
                "messages": [{"role": "user", "content": content}],
                "temperature": 0.2,
            }
            response = requests.post(
                f"{self.base_url}/compatible-mode/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=45,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            return f"[fallback_description] {merged_hint or 'empty_content'}"

    def parse_structured_description(self, raw_text: str) -> dict:
        fallback = {
            "topic": "other",
            "stance": "neutral",
            "emotion_score": 3,
            "summary": raw_text[:200] if raw_text else "",
        }
        if not raw_text:
            return fallback
        candidate = raw_text.strip()
        if "```" in candidate:
            blocks = re.findall(r"```(?:json)?\s*(.*?)```", candidate, flags=re.S)
            if blocks:
                candidate = blocks[0].strip()
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]
        try:
            obj = json.loads(candidate)
            topic = str(obj.get("topic", "other")).strip().lower() or "other"
            stance = str(obj.get("stance", "neutral")).strip().lower() or "neutral"
            if stance not in {"left", "center", "right", "neutral"}:
                stance = "neutral"
            emotion = int(obj.get("emotion_score", 3))
            emotion = max(1, min(5, emotion))
            summary = str(obj.get("summary", "")).strip()
            return {"topic": topic, "stance": stance, "emotion_score": emotion, "summary": summary}
        except Exception:
            return fallback

    def embed_multimodal(self, text: str, image_url: str | None = None, video_frame: str | None = None) -> np.ndarray:
        merged_text = " ".join([x for x in [text, image_url or "", video_frame or ""] if x]).strip()
        if not merged_text:
            merged_text = "empty_content"
        return self.embed_text_batch([merged_text])[0]
