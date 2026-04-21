from __future__ import annotations

import time
import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.llm import get_llm_provider

router = APIRouter(prefix="/llm", tags=["llm"])


class InvokeTestIn(BaseModel):
    prompt: str = Field(default="请返回一个JSON对象，包含status和message字段。", min_length=1, max_length=4000)
    response_mode: Literal["text", "json", "multimodal"] = "json"
    model: str | None = None
    image_url: str | None = None
    temperature: float = Field(default=0.2, ge=0.0, le=1.5)


@router.get("/health")
def llm_health() -> dict:
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    health = get_llm_provider().health()
    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    return {
        "ok": health.ok,
        "provider": health.provider,
        "inference_mode": health.inference_mode,
        "embedding_model": health.embedding_model,
        "multimodal_model": health.multimodal_model,
        "report_model": health.report_model,
        "capabilities": health.capabilities or [],
        "detail": health.detail,
        "request_id": request_id,
        "latency_ms": latency_ms,
    }


@router.get("/providers")
def llm_providers() -> dict:
    health = get_llm_provider().health()
    return {
        "active_provider": health.provider,
        "inference_mode": health.inference_mode,
        "providers": [
            {"name": "dashscope", "available": health.provider == "dashscope"},
            {"name": "local", "available": health.provider == "local"},
        ],
    }


@router.post("/invoke-test")
def llm_invoke_test(payload: InvokeTestIn) -> dict:
    provider = get_llm_provider()
    health = provider.health()
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    try:
        if payload.response_mode == "json":
            result = provider.invoke_json(
                prompt=payload.prompt,
                model=payload.model,
                temperature=payload.temperature,
                retry_on_parse_error=True,
            )
        elif payload.response_mode == "multimodal":
            result = provider.invoke_multimodal(
                prompt=payload.prompt,
                model=payload.model,
                image_url=payload.image_url,
                temperature=payload.temperature,
            )
        else:
            result = provider.invoke_text(
                prompt=payload.prompt,
                model=payload.model,
                temperature=payload.temperature,
            )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"llm invoke failed ({request_id}): {exc}") from exc
    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    return {
        "request_id": request_id,
        "provider": health.provider,
        "model": result.model,
        "latency_ms": latency_ms,
        "finish_reason": result.finish_reason,
        "usage": result.usage,
        "content": result.content,
        "parsed_json": result.parsed_json,
    }
