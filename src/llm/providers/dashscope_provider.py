from __future__ import annotations

import hashlib
import json
import re
import time

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


class DashScopeProvider(LlmProvider):
    def __init__(self) -> None:
        self.api_key = settings.dashscope_api_key
        self.base_url = settings.dashscope_base_url.rstrip("/")
        self.embedding_model = settings.text_embedding_model
        self.multimodal_model = settings.omni_model
        self.report_model = settings.report_model

    def _post_with_retry(self, path: str, payload: dict, timeout_seconds: float | None = None) -> dict:
        timeout = timeout_seconds or settings.llm_request_timeout_seconds
        retries = max(0, settings.llm_max_retries)
        base_backoff = max(0.0, settings.llm_retry_backoff_seconds)
        url = f"{self.base_url}{path}"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    timeout=timeout,
                )
                status = response.status_code
                if status == 429 or status >= 500:
                    if attempt < retries:
                        time.sleep(base_backoff * (2**attempt))
                        continue
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else None
                if status is not None and status < 500 and status != 429:
                    raise
                if attempt < retries:
                    time.sleep(base_backoff * (2**attempt))
                    continue
                raise
            except requests.RequestException as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(base_backoff * (2**attempt))
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise RuntimeError("DashScope request failed without an explicit error.")

    def _chat_completion(self, *, prompt: str, model: str | None = None, temperature: float = 0.2) -> str:
        if not self.api_key:
            return ""
        payload = {
            "model": model or self.multimodal_model,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            "temperature": temperature,
        }
        data = self._post_with_retry("/compatible-mode/v1/chat/completions", payload)
        return str(data["choices"][0]["message"]["content"])

    def _extract_content(self, data: dict) -> str:
        message = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content", "")
        if isinstance(message, str):
            return message
        if isinstance(message, list):
            chunks = []
            for part in message:
                if isinstance(part, dict) and "text" in part:
                    chunks.append(str(part["text"]))
                else:
                    chunks.append(str(part))
            return "".join(chunks).strip()
        return str(message)

    def invoke_text(self, *, prompt: str, model: str | None = None, temperature: float = 0.2) -> LlmInvokeResult:
        if not self.api_key:
            return LlmInvokeResult(
                content="",
                usage={},
                raw=None,
                model=model or self.multimodal_model,
                finish_reason="missing_api_key",
            )
        payload = {
            "model": model or self.multimodal_model,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            "temperature": temperature,
        }
        data = self._post_with_retry("/compatible-mode/v1/chat/completions", payload)
        finish_reason = str(((data.get("choices") or [{}])[0]).get("finish_reason", ""))
        return LlmInvokeResult(
            content=self._extract_content(data),
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
        parsed = extract_json_payload(result.content)
        if parsed is not None:
            result.parsed_json = parsed
            return result
        if retry_on_parse_error and self.api_key:
            retry_prompt = (
                f"{prompt}\n\n"
                "上一个回答不是严格JSON。请只返回一个有效JSON对象或JSON数组，不要输出额外文本。"
            )
            retry_result = self.invoke_text(prompt=retry_prompt, model=model, temperature=0.0)
            retry_result.parsed_json = extract_json_payload(retry_result.content)
            return retry_result
        return result

    def invoke_multimodal(
        self,
        *,
        prompt: str,
        image_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> LlmInvokeResult:
        if not self.api_key:
            return LlmInvokeResult(
                content="",
                usage={},
                raw=None,
                model=model or self.multimodal_model,
                finish_reason="missing_api_key",
            )
        content: list[dict] = [{"type": "text", "text": prompt}]
        if image_url:
            content.append({"type": "image_url", "image_url": {"url": image_url}})
        payload = {
            "model": model or self.multimodal_model,
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
        }
        data = self._post_with_retry("/compatible-mode/v1/chat/completions", payload)
        finish_reason = str(((data.get("choices") or [{}])[0]).get("finish_reason", ""))
        return LlmInvokeResult(
            content=self._extract_content(data),
            usage=(data.get("usage") if isinstance(data.get("usage"), dict) else {}),
            raw=data,
            model=str(data.get("model", model or self.multimodal_model)),
            finish_reason=finish_reason,
        )

    def _fallback_embedding(self, text: str, dim: int = 64) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        base = np.frombuffer(digest, dtype=np.uint8).astype(np.float32)
        repeated = np.resize(base, dim)
        norm = np.linalg.norm(repeated) or 1.0
        return repeated / norm

    def health(self) -> LlmHealth:
        if not self.api_key:
            return LlmHealth(
                ok=False,
                provider="dashscope",
                inference_mode="remote",
                embedding_model=self.embedding_model,
                multimodal_model=self.multimodal_model,
                report_model=self.report_model,
                capabilities=["extract_semantics", "embed_text_batch", "embed_multimodal"],
                detail="DASHSCOPE_API_KEY is empty",
            )
        return LlmHealth(
            ok=True,
            provider="dashscope",
            inference_mode="remote",
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
        )

    def embed_text_batch(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            if not self.api_key:
                vectors.append(self._fallback_embedding(text))
                continue
            payload = self._post_with_retry(
                "/compatible-mode/v1/embeddings",
                {"model": self.embedding_model, "input": text},
                timeout_seconds=min(30, settings.llm_request_timeout_seconds),
            )
            vectors.append(np.array(payload["data"][0]["embedding"], dtype=np.float32))
        return np.vstack(vectors)

    def _describe_multimodal_content(self, text: str, image_url: str | None = None, video_hint: str | None = None) -> str:
        merged_hint = " ".join([x for x in [text, video_hint or ""] if x]).strip()
        if not self.api_key:
            return f"[fallback_description] {merged_hint or 'empty_content'}"
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
        prompt = content[0]["text"]
        return self._chat_completion(prompt=prompt, model=self.multimodal_model, temperature=0.2)

    def _parse_structured_description(self, raw_text: str) -> dict[str, object]:
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
            emotion = max(1, min(5, int(obj.get("emotion_score", 3))))
            summary = str(obj.get("summary", "")).strip()
            return {"topic": topic, "stance": stance, "emotion_score": emotion, "summary": summary}
        except Exception:
            return fallback

    def extract_semantics(
        self,
        text: str,
        image_url: str | None = None,
        video_hint: str | None = None,
    ) -> SemanticExtraction:
        description = self._describe_multimodal_content(text=text, image_url=image_url, video_hint=video_hint)
        parsed = self._parse_structured_description(description)
        return SemanticExtraction(
            raw_description=description,
            topic=str(parsed["topic"]),
            stance=str(parsed["stance"]),
            emotion_score=int(parsed["emotion_score"]),
            summary=str(parsed["summary"]),
        )

    def embed_multimodal(self, text: str, image_url: str | None = None, video_frame: str | None = None) -> np.ndarray:
        merged_text = " ".join([x for x in [text, image_url or "", video_frame or ""] if x]).strip()
        if not merged_text:
            merged_text = "empty_content"
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
        prompt = (
            "你是多模态信息理解引擎。请严格输出JSON对象，不要输出多余文本。"
            "字段: frame_summary, audio_transcript, subtitle_summary, bullet_comments_summary, normalized_description。"
            f"\ntext={text}\nvideo_hint={video_hint or ''}\nsubtitles={subtitles[:30]}\nbullet_comments={bullet_comments[:30]}"
        )
        if not self.api_key:
            normalized = " ".join([text, video_hint or "", " ".join(subtitles[:3]), " ".join(bullet_comments[:3])]).strip()
            return MultimodalParseResult(
                text=text,
                frame_summary=video_hint or "",
                audio_transcript="",
                subtitle_summary=" ".join(subtitles[:5]).strip(),
                bullet_comments_summary=" ".join(bullet_comments[:5]).strip(),
                normalized_description=normalized[:800],
            )
        raw = self._chat_completion(prompt=prompt, model=self.multimodal_model, temperature=0.1)
        parsed = self._parse_structured_description(raw_text=raw)
        return MultimodalParseResult(
            text=text,
            frame_summary=str(parsed.get("summary", "")),
            audio_transcript=str(parsed.get("summary", "")),
            subtitle_summary=" ".join(subtitles[:8]).strip(),
            bullet_comments_summary=" ".join(bullet_comments[:8]).strip(),
            normalized_description=str(parsed.get("summary", "")),
        )

    def generate_strategy_plan(
        self,
        *,
        blindspots: list[str],
        top_topics: list[str],
        history_notes: list[str],
    ) -> list[StrategyPlanResult]:
        prompt = (
            "你是破茧策略规划助手。输出JSON数组，每项字段: level, topic, reason, confidence(0-1)。"
            f"\nblindspots={blindspots}\ntop_topics={top_topics}\nhistory_notes={history_notes[:20]}"
        )
        if not self.api_key:
            seeds = blindspots or ["society", "history", "science"]
            return [
                StrategyPlanResult(level="L1", topic=f"{top_topics[0] if top_topics else 'technology'}+{seeds[0]}", reason="从相邻兴趣切入", confidence=0.72),
                StrategyPlanResult(level="L2", topic=seeds[min(1, len(seeds) - 1)], reason="扩展跨领域曝光", confidence=0.68),
                StrategyPlanResult(level="L3", topic=seeds[min(2, len(seeds) - 1)], reason="挑战认知盲区", confidence=0.64),
            ]
        raw = self._chat_completion(prompt=prompt, model=self.report_model, temperature=0.3)
        items = []
        try:
            candidate = raw
            if "```" in candidate:
                blocks = re.findall(r"```(?:json)?\s*(.*?)```", candidate, flags=re.S)
                if blocks:
                    candidate = blocks[0].strip()
            arr = json.loads(candidate)
            if isinstance(arr, list):
                for it in arr[:5]:
                    if not isinstance(it, dict):
                        continue
                    items.append(
                        StrategyPlanResult(
                            level=str(it.get("level", "L1")),
                            topic=str(it.get("topic", "other")),
                            reason=str(it.get("reason", "")),
                            confidence=max(0.0, min(1.0, float(it.get("confidence", 0.6)))),
                        )
                    )
        except Exception:
            items = []
        if items:
            return items
        seeds = blindspots or ["society", "history", "science"]
        return [
            StrategyPlanResult(level="L1", topic=f"{top_topics[0] if top_topics else 'technology'}+{seeds[0]}", reason="从相邻兴趣切入", confidence=0.72),
            StrategyPlanResult(level="L2", topic=seeds[min(1, len(seeds) - 1)], reason="扩展跨领域曝光", confidence=0.68),
            StrategyPlanResult(level="L3", topic=seeds[min(2, len(seeds) - 1)], reason="挑战认知盲区", confidence=0.64),
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
        prompt = (
            "你是认知训练评阅器。请输出JSON对象，字段: score(0-1), feedback, evidence(list[str])。"
            f"\n主题:{topic}\n正方:{pro_view}\n反方:{con_view}\n学员总结:{summary}\n反思:{reflection}"
        )
        if not self.api_key:
            score = 0.2
            if summary.strip():
                score += 0.4
            if reflection.strip():
                score += 0.2
            if any(k in summary for k in ("但是", "同时", "另一方面", "然而")):
                score += 0.2
            return TrainingReviewResult(
                score=round(min(1.0, score), 3),
                feedback="已基于双边观点完整性与反思深度完成评阅。",
                evidence=[summary[:80], reflection[:80]],
            )
        raw = self._chat_completion(prompt=prompt, model=self.report_model, temperature=0.2)
        try:
            candidate = raw
            if "```" in candidate:
                blocks = re.findall(r"```(?:json)?\s*(.*?)```", candidate, flags=re.S)
                if blocks:
                    candidate = blocks[0].strip()
            data = json.loads(candidate)
            return TrainingReviewResult(
                score=max(0.0, min(1.0, float(data.get("score", 0.0)))),
                feedback=str(data.get("feedback", "")),
                evidence=[str(x) for x in (data.get("evidence", []) or [])[:5]],
            )
        except Exception:
            return TrainingReviewResult(score=0.0, feedback="评阅失败，已返回稳态结果。", evidence=[])
