from __future__ import annotations

from fastapi import APIRouter

from src.llm import get_llm_provider

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/health")
def llm_health() -> dict:
    health = get_llm_provider().health()
    return {
        "ok": health.ok,
        "provider": health.provider,
        "embedding_model": health.embedding_model,
        "multimodal_model": health.multimodal_model,
        "detail": health.detail,
    }
