from __future__ import annotations

import hashlib
import json

import numpy as np
import requests

from src.config.settings import settings
from src.llm.gateway import (
    extract_json_payload,
    LlmHealth,
    LlmInvokeResult,
    LlmProvider,
    MultimodalParseResult,
    SemanticExtraction,
    StrategyPlanResult,
    TrainingReviewResult,
)


class LocalProvider(LlmProvider):
    def __init__(self) -> None:
        self.embedding_model = settings.local_embedding_model
        self.base_multimodal_model = settings.local_multimodal_model
        self.multimodal_model = settings.active_local_chat_model()
        self.report_model = settings.active_local_chat_model()
        self.base_url = settings.local_openai_base_url.rstrip("/")
        self.api_key = settings.local_openai_api_key
        self._ready_cache: bool | None = None
        self._ready_detail = ""

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _chat_completion(self, *, prompt: str, model: str | None = None, temperature: float = 0.2) -> str:
        payload = {
            "model": model or self.multimodal_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            timeout=12,
        )
        response.raise_for_status()
        data = response.json()
        return str(data["choices"][0]["message"]["content"])

    def invoke_text(self, *, prompt: str, model: str | None = None, temperature: float = 0.2) -> LlmInvokeResult:
        ok, detail = self._check_ready()
        if not ok:
            return LlmInvokeResult(
                content="",
                usage={},
                raw=None,
                model=model or self.multimodal_model,
                finish_reason=detail or "local_unavailable",
            )
        payload = {
            "model": model or self.multimodal_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            timeout=min(12, settings.llm_request_timeout_seconds),
        )
        response.raise_for_status()
        data = response.json()
        finish_reason = str(((data.get("choices") or [{}])[0]).get("finish_reason", ""))
        content = str((((data.get("choices") or [{}])[0]).get("message") or {}).get("content", ""))
        return LlmInvokeResult(
            content=content,
            usage=(data.get("usage") if isinstance(data.get("usage"), dict) else {}),
            raw=data,
            model=str(data.get("model", model or self.multimodal_model)),
            finish_reason=finish_reason,
        )

    def invoke_json(
        self,
        *,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        retry_on_parse_error: bool = True,
    ) -> LlmInvokeResult:
        result = self.invoke_text(prompt=prompt, model=model, temperature=temperature)
        result.parsed_json = extract_json_payload(result.content)
        return result

    def invoke_multimodal(
        self,
        *,
        prompt: str,
        image_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> LlmInvokeResult:
        merged_prompt = prompt if not image_url else f"{prompt}\nimage_url={image_url}"
        return self.invoke_text(prompt=merged_prompt, model=model or self.multimodal_model, temperature=temperature)

    def _check_ready(self) -> tuple[bool, str]:
        if self._ready_cache is not None:
            return self._ready_cache, self._ready_detail
        try:
            resp = requests.get(f"{self.base_url}/models", headers=self._headers(), timeout=2)
            resp.raise_for_status()
            self._ready_cache = True
            self._ready_detail = "local openai-compatible endpoint ready"
        except Exception as exc:
            self._ready_cache = False
            self._ready_detail = f"local endpoint not ready: {exc.__class__.__name__}"
        return self._ready_cache, self._ready_detail

    def _fallback_embedding(self, text: str, dim: int = 64) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        base = np.frombuffer(digest, dtype=np.uint8).astype(np.float32)
        repeated = np.resize(base, dim)
        norm = np.linalg.norm(repeated) or 1.0
        return repeated / norm

    def health(self) -> LlmHealth:
        ok, detail = self._check_ready()
        model_hint = f"active_chat_model={self.multimodal_model}; base_model={self.base_multimodal_model}"
        if detail:
            detail = f"{detail}; {model_hint}"
        else:
            detail = model_hint
        return LlmHealth(
            ok=ok,
            provider="local",
            inference_mode="local",
            embedding_model=self.embedding_model,
            multimodal_model=self.multimodal_model,
            report_model=self.report_model,
            capabilities=[
                "extract_semantics",
                "embed_text_batch",
                "embed_multimodal",
                "parse_multimodal_context",
                "generate_strategy_plan",
                "review_training_submission",
            ],
            detail=detail,
        )

    def extract_semantics(
        self,
        text: str,
        image_url: str | None = None,
        video_hint: str | None = None,
    ) -> SemanticExtraction:
        prompt = (
            "返回JSON对象: topic, stance(left|center|right|neutral), emotion_score(1-5), summary。"
            f"\ntext={text}\nimage_url={image_url or ''}\nvideo_hint={video_hint or ''}"
        )
        ok, _ = self._check_ready()
        if not ok:
            return SemanticExtraction(
                raw_description=f"[local_fallback] {text[:120]}",
                topic="other",
                stance="neutral",
                emotion_score=3,
                summary=text[:120],
            )
        try:
            raw = self._chat_completion(prompt=prompt, model=self.multimodal_model, temperature=0.1)
            parsed = json.loads(raw)
            return SemanticExtraction(
                raw_description=raw,
                topic=str(parsed.get("topic", "other")),
                stance=str(parsed.get("stance", "neutral")),
                emotion_score=max(1, min(5, int(parsed.get("emotion_score", 3)))),
                summary=str(parsed.get("summary", text[:120])),
            )
        except Exception:
            return SemanticExtraction(
                raw_description=f"[local_fallback] {text[:120]}",
                topic="other",
                stance="neutral",
                emotion_score=3,
                summary=text[:120],
            )

    def embed_text_batch(self, texts: list[str]) -> np.ndarray:
        ok, _ = self._check_ready()
        if not ok:
            vectors = [self._fallback_embedding(text) for text in texts]
            return np.vstack(vectors)
        vectors = []
        for text in texts:
            try:
                payload = {"model": self.embedding_model, "input": text}
                response = requests.post(
                    f"{self.base_url}/embeddings",
                    headers=self._headers(),
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    timeout=10,
                )
                response.raise_for_status()
                data = response.json()
                vectors.append(np.asarray(data["data"][0]["embedding"], dtype=np.float32))
            except Exception:
                vectors.append(self._fallback_embedding(text))
        return np.vstack(vectors)

    def embed_multimodal(self, text: str, image_url: str | None = None, video_frame: str | None = None) -> np.ndarray:
        merged_text = " ".join([x for x in [text, image_url or "", video_frame or ""] if x]).strip() or "empty_content"
        return self.embed_text_batch([merged_text])[0]

    def parse_multimodal_context(
        self,
        *,
        text: str,
        video_hint: str | None = None,
        subtitles: list[str] | None = None,
        bullet_comments: list[str] | None = None,
    ) -> MultimodalParseResult:
        subtitles = subtitles or []
        bullet_comments = bullet_comments or []
        normalized = " ".join([text, video_hint or "", " ".join(subtitles[:5]), " ".join(bullet_comments[:5])]).strip()
        return MultimodalParseResult(
            text=text,
            frame_summary=video_hint or "",
            audio_transcript="",
            subtitle_summary=" ".join(subtitles[:5]).strip(),
            bullet_comments_summary=" ".join(bullet_comments[:5]).strip(),
            normalized_description=normalized[:800],
        )

    def generate_strategy_plan(
        self,
        *,
        blindspots: list[str],
        top_topics: list[str],
        history_notes: list[str],
    ) -> list[StrategyPlanResult]:
        seeds = blindspots or ["society", "history", "science"]
        base = top_topics[0] if top_topics else "technology"
        return [
            StrategyPlanResult(level="L1", topic=f"{base}+{seeds[0]}", reason="从邻域话题引入跨域内容", confidence=0.7),
            StrategyPlanResult(level="L2", topic=seeds[min(1, len(seeds) - 1)], reason="提升跨领域曝光", confidence=0.65),
            StrategyPlanResult(level="L3", topic=seeds[min(2, len(seeds) - 1)], reason="补齐认知盲区", confidence=0.6),
        ]

    def review_training_submission(
        self,
        *,
        topic: str,
        pro_view: str,
        con_view: str,
        summary: str,
        reflection: str,
    ) -> TrainingReviewResult:
        score = 0.2
        if summary.strip():
            score += 0.4
        if reflection.strip():
            score += 0.2
        if any(k in summary for k in ("但是", "同时", "另一方面", "然而", "however", "while")):
            score += 0.2
        return TrainingReviewResult(
            score=round(min(1.0, score), 3),
            feedback=f"已根据议题“{topic}”完成本地评阅，建议增加跨领域证据。",
            evidence=[summary[:80], reflection[:80]],
        )
