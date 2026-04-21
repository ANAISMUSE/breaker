from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.embedding.dashscope_client import DashScopeClient
from src.embedding.vector_store import LocalVectorStore

try:
    from docarray import BaseDoc, DocList
    from docarray.typing import NdArray
except Exception:  # pragma: no cover - runtime fallback
    BaseDoc = object  # type: ignore[assignment]
    DocList = list  # type: ignore[assignment]
    NdArray = np.ndarray  # type: ignore[assignment]
    DOCARRAY_AVAILABLE = False
else:  # pragma: no cover - import-time branch
    DOCARRAY_AVAILABLE = True

try:
    from fastembed import SparseTextEmbedding
except Exception:  # pragma: no cover - runtime fallback
    SparseTextEmbedding = None  # type: ignore[assignment]


@dataclass
class _CompressionResult:
    dense: np.ndarray
    sparse_tokens: list[int]
    sparse_weights: list[float]


@dataclass
class _EvidenceFragment:
    modality: str
    source: str
    text: str
    confidence: float = 0.8


@dataclass
class _UnifiedMultimodalRepresentation:
    content_id: str
    platform: str
    topic: str
    semantic_summary: str
    normalized_description: str
    frame_summary: str
    audio_transcript: str
    subtitle_summary: str
    bullet_comments_summary: str
    image_description: str
    evidence: list[_EvidenceFragment]
    schema_version: str = "mm_v1"

    def to_metadata(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "normalized_description": self.normalized_description,
            "frame_summary": self.frame_summary,
            "audio_transcript": self.audio_transcript,
            "subtitle_summary": self.subtitle_summary,
            "bullet_comments_summary": self.bullet_comments_summary,
            "image_description": self.image_description,
            "evidence": [
                {
                    "modality": item.modality,
                    "source": item.source,
                    "text": item.text,
                    "confidence": float(item.confidence),
                }
                for item in self.evidence
                if item.text
            ],
        }


class _MultimodalDoc(BaseDoc):  # type: ignore[misc]
    content_id: str
    platform: str
    topic: str
    semantic_summary: str
    embedding: NdArray
    text_embedding: NdArray
    visual_embedding: NdArray


def _safe_sparse_embed(text: str) -> tuple[list[int], list[float]]:
    if os.getenv("ENABLE_FASTEMBED", "false").lower() != "true":
        return [], []
    if SparseTextEmbedding is None:
        return [], []
    try:
        model = _get_sparse_model()
        if model is None:
            return [], []
        out = list(model.embed([text]))
        if not out:
            return [], []
        sparse = out[0]
        indices = [int(x) for x in list(getattr(sparse, "indices", []))[:128]]
        values = [float(x) for x in list(getattr(sparse, "values", []))[:128]]
        return indices, values
    except Exception:
        return [], []


_SPARSE_MODEL: Any | None = None


def _get_sparse_model() -> Any | None:
    global _SPARSE_MODEL
    if SparseTextEmbedding is None:
        return None
    if _SPARSE_MODEL is None:
        _SPARSE_MODEL = SparseTextEmbedding(model_name="Qdrant/bm42-all-minilm-l6-v2-attentions")
    return _SPARSE_MODEL


def _compress_dense(vector: np.ndarray, target_dim: int = 128) -> np.ndarray:
    arr = np.asarray(vector, dtype=np.float32).ravel()
    if arr.size <= target_dim:
        return arr
    # Lightweight deterministic compression: segment average pooling.
    step = arr.size / float(target_dim)
    out = np.zeros(target_dim, dtype=np.float32)
    for i in range(target_dim):
        start = int(i * step)
        end = int((i + 1) * step)
        if end <= start:
            end = min(start + 1, arr.size)
        out[i] = float(arr[start:end].mean())
    norm = np.linalg.norm(out) or 1.0
    return out / norm


def _build_compression(vector: np.ndarray, text: str) -> _CompressionResult:
    dense = _compress_dense(vector, target_dim=128)
    sparse_tokens, sparse_weights = _safe_sparse_embed(text)
    return _CompressionResult(dense=dense, sparse_tokens=sparse_tokens, sparse_weights=sparse_weights)


def _build_unified_representation(
    row: dict[str, Any], parsed_mm: Any, extraction: Any, image_description: str
) -> _UnifiedMultimodalRepresentation:
    evidence = [
        _EvidenceFragment(modality="video", source="frame_summary", text=str(parsed_mm.frame_summary)),
        _EvidenceFragment(modality="audio", source="audio_transcript", text=str(parsed_mm.audio_transcript)),
        _EvidenceFragment(modality="subtitle", source="subtitle_summary", text=str(parsed_mm.subtitle_summary)),
        _EvidenceFragment(
            modality="bullet_comment",
            source="bullet_comments_summary",
            text=str(parsed_mm.bullet_comments_summary),
        ),
        _EvidenceFragment(modality="image", source="image_description", text=image_description),
        _EvidenceFragment(modality="text", source="semantic_summary", text=str(extraction.summary)),
    ]
    return _UnifiedMultimodalRepresentation(
        content_id=str(row.get("content_id", "")),
        platform=str(row.get("platform", "")),
        topic=str(row.get("topic", "other")),
        semantic_summary=str(extraction.summary),
        normalized_description=str(parsed_mm.normalized_description),
        frame_summary=str(parsed_mm.frame_summary),
        audio_transcript=str(parsed_mm.audio_transcript),
        subtitle_summary=str(parsed_mm.subtitle_summary),
        bullet_comments_summary=str(parsed_mm.bullet_comments_summary),
        image_description=image_description,
        evidence=evidence,
    )


def _persist_docarray_snapshot(
    docs: list[_MultimodalDoc] | Any,
    *,
    store_path: str,
    schema_version: str,
) -> str | None:
    if not docs:
        return None
    path = Path(store_path)
    out = path.with_suffix(".docarray.json")
    payload = {
        "schema_version": schema_version,
        "count": len(docs),
        "items": [
            {
                "content_id": str(getattr(doc, "content_id", "")),
                "platform": str(getattr(doc, "platform", "")),
                "topic": str(getattr(doc, "topic", "other")),
                "semantic_summary": str(getattr(doc, "semantic_summary", "")),
                "embedding_fused": np.asarray(getattr(doc, "embedding"), dtype=np.float32).ravel().tolist(),
                "embedding_text": np.asarray(getattr(doc, "text_embedding"), dtype=np.float32).ravel().tolist(),
                "embedding_visual": np.asarray(getattr(doc, "visual_embedding"), dtype=np.float32).ravel().tolist(),
            }
            for doc in docs
        ],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out)


def build_semantic_vector_store(
    df: pd.DataFrame, store_path: str = "data/vector_store.json"
) -> tuple[LocalVectorStore, pd.DataFrame]:
    client = DashScopeClient()
    store = LocalVectorStore(base_path=store_path)
    enriched_rows = []
    docs = DocList[_MultimodalDoc]() if DOCARRAY_AVAILABLE else []

    for row in df.to_dict(orient="records"):
        # Stage-1: multimodal understanding/description by Omni model
        subtitles = row.get("subtitles")
        bullet_comments = row.get("bullet_comments")
        subtitles_list = subtitles if isinstance(subtitles, list) else []
        comments_list = bullet_comments if isinstance(bullet_comments, list) else []
        parsed_mm = client.provider.parse_multimodal_context(
            text=str(row.get("text", "")),
            video_hint=str(row.get("video_url", "")) or None,
            subtitles=[str(x) for x in subtitles_list],
            bullet_comments=[str(x) for x in comments_list],
        )
        extraction = client.provider.extract_semantics(
            text=parsed_mm.normalized_description or str(row.get("text", "")),
            image_url=str(row.get("image_url", "")) or None,
            video_hint=str(row.get("video_url", "")) or None,
        )
        image_extraction = client.provider.extract_semantics(
            text="请总结图片关键信息",
            image_url=str(row.get("image_url", "")) or None,
            video_hint=None,
        )
        representation = _build_unified_representation(
            row=row,
            parsed_mm=parsed_mm,
            extraction=extraction,
            image_description=str(image_extraction.summary or ""),
        )
        if extraction.topic:
            row["topic"] = extraction.topic
        row["stance"] = extraction.stance or row.get("stance", "neutral")
        row["emotion_score"] = extraction.emotion_score or row.get("emotion_score", 3)
        row["semantic_summary"] = extraction.summary
        row["semantic_description"] = extraction.raw_description
        row["frame_summary"] = representation.frame_summary
        row["audio_transcript"] = representation.audio_transcript
        row["subtitle_summary"] = representation.subtitle_summary
        row["bullet_comments_summary"] = representation.bullet_comments_summary
        row["image_description"] = representation.image_description
        row["multimodal_schema_version"] = representation.schema_version
        row["multimodal_evidence"] = representation.to_metadata()["evidence"]
        merged_for_embedding = (
            f"{str(row.get('text', ''))}\n{representation.normalized_description}\n{extraction.summary}".strip()
        )
        enriched_rows.append(row)

        # Stage-2: semantic embedding for retrieval/evaluation
        fused_vector = client.embed_multimodal(
            text=merged_for_embedding,
            image_url=str(row.get("image_url", "")) or None,
            video_frame=str(row.get("video_url", "")) or None,
        )
        text_vector = client.embed_text_batch([str(row.get("text", ""))])[0]
        visual_hint = " ".join([str(row.get("image_url", "")), str(row.get("video_url", ""))]).strip() or merged_for_embedding
        visual_vector = client.embed_text_batch([visual_hint])[0]
        compression = _build_compression(fused_vector, merged_for_embedding)
        row["embedding"] = fused_vector
        row["embedding_fused"] = fused_vector
        row["embedding_text"] = text_vector
        row["embedding_visual"] = visual_vector
        row["embedding_compressed"] = compression.dense
        row["embedding_sparse_tokens"] = compression.sparse_tokens
        row["embedding_sparse_weights"] = compression.sparse_weights
        store.add(
            fused_vector,
            {
                "content_id": row.get("content_id"),
                "topic": row.get("topic"),
                "timestamp": str(row.get("timestamp")),
                "platform": row.get("platform"),
                "semantic_description": extraction.raw_description,
                "semantic_summary": extraction.summary,
                "stance": row.get("stance"),
                "emotion_score": row.get("emotion_score"),
                "frame_summary": row.get("frame_summary", ""),
                "audio_transcript": row.get("audio_transcript", ""),
                "subtitle_summary": row.get("subtitle_summary", ""),
                "bullet_comments_summary": row.get("bullet_comments_summary", ""),
                "image_description": row.get("image_description", ""),
                "multimodal_schema_version": row.get("multimodal_schema_version", "mm_v1"),
                "multimodal_evidence": row.get("multimodal_evidence", []),
                "sparse_tokens": compression.sparse_tokens,
                "sparse_weights": compression.sparse_weights,
            },
            vector_bundle={
                "fused": np.asarray(fused_vector, dtype=np.float32),
                "text": np.asarray(text_vector, dtype=np.float32),
                "visual": np.asarray(visual_vector, dtype=np.float32),
                "compressed": np.asarray(compression.dense, dtype=np.float32),
            },
            version="v2",
            metadata_version="m2",
        )
        if DOCARRAY_AVAILABLE:
            docs.append(
                _MultimodalDoc(
                    content_id=str(row.get("content_id", "")),
                    platform=str(row.get("platform", "")),
                    topic=str(row.get("topic", "other")),
                    semantic_summary=str(row.get("semantic_summary", "")),
                    embedding=np.asarray(fused_vector, dtype=np.float32),
                    text_embedding=np.asarray(text_vector, dtype=np.float32),
                    visual_embedding=np.asarray(visual_vector, dtype=np.float32),
                )
            )
    store.save()
    docarray_snapshot = _persist_docarray_snapshot(
        docs,
        store_path=store_path,
        schema_version="mm_v1",
    )
    enriched_df = pd.DataFrame(enriched_rows)
    if not enriched_df.empty:
        enriched_df.attrs["docarray_count"] = len(docs)
        enriched_df.attrs["docarray_snapshot_path"] = docarray_snapshot
        enriched_df.attrs["vector_schema_version"] = "v2"
        enriched_df.attrs["multimodal_schema_version"] = "mm_v1"
    return store, enriched_df
