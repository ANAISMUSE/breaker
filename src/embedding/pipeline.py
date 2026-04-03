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
        description = client.describe_multimodal_content(
            text=str(row.get("text", "")),
            image_url=str(row.get("image_url", "")) or None,
            video_hint=str(row.get("video_url", "")) or None,
        )
        parsed = client.parse_structured_description(description)
        if parsed.get("topic"):
            row["topic"] = parsed["topic"]
        row["stance"] = parsed.get("stance", row.get("stance", "neutral"))
        row["emotion_score"] = parsed.get("emotion_score", row.get("emotion_score", 3))
        merged_for_embedding = f"{str(row.get('text', ''))}\n{parsed.get('summary', '')}".strip()
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
                "semantic_description": description,
                "semantic_summary": parsed.get("summary", ""),
                "stance": row.get("stance"),
                "emotion_score": row.get("emotion_score"),
            },
        )
    store.save()
    enriched_df = pd.DataFrame(enriched_rows)
    return store, enriched_df
