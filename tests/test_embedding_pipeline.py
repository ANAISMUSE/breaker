import pandas as pd

from src.embedding.pipeline import build_semantic_vector_store


def test_build_semantic_vector_store() -> None:
    df = pd.DataFrame(
        [
            {
                "text": "AI 科技新闻",
                "image_url": "",
                "video_url": "",
                "content_id": "1",
                "topic": "technology",
                "timestamp": "2026-03-31 10:00:00",
                "platform": "douyin",
            }
        ]
    )
    store, enriched_df = build_semantic_vector_store(df, store_path="data/test_vector_store.json")
    assert len(store.vectors) == 1
    assert "stance" in enriched_df.columns
