from __future__ import annotations

import pandas as pd

from src.embedding.dashscope_client import DashScopeClient
from src.embedding.vector_store import LocalVectorStore


def build_semantic_vector_store(
    df: pd.DataFrame, store_path: str = "data/vector_store.json"
) -> tuple[LocalVectorStore, pd.DataFrame]:
    client = DashScopeClient()
    store = LocalVectorStore(base_path=store_path)
    enriched_rows = []

    for row in df.to_dict(orient="records"):
        # Stage-1: multimodal understanding/description by Omni model
        extraction = client.provider.extract_semantics(
            text=str(row.get("text", "")),
            image_url=str(row.get("image_url", "")) or None,
            video_hint=str(row.get("video_url", "")) or None,
        )
        if extraction.topic:
            row["topic"] = extraction.topic
        row["stance"] = extraction.stance or row.get("stance", "neutral")
        row["emotion_score"] = extraction.emotion_score or row.get("emotion_score", 3)
        row["semantic_summary"] = extraction.summary
        row["semantic_description"] = extraction.raw_description
        merged_for_embedding = f"{str(row.get('text', ''))}\n{extraction.summary}".strip()
        enriched_rows.append(row)

        # Stage-2: semantic embedding for retrieval/evaluation
        vector = client.embed_multimodal(
            text=merged_for_embedding,
            image_url=str(row.get("image_url", "")) or None,
            video_frame=str(row.get("video_url", "")) or None,
        )
        row["embedding"] = vector
        store.add(
            vector,
            {
                "content_id": row.get("content_id"),
                "topic": row.get("topic"),
                "timestamp": str(row.get("timestamp")),
                "platform": row.get("platform"),
                "semantic_description": extraction.raw_description,
                "semantic_summary": extraction.summary,
                "stance": row.get("stance"),
                "emotion_score": row.get("emotion_score"),
            },
        )
    store.save()
    enriched_df = pd.DataFrame(enriched_rows)
    return store, enriched_df
