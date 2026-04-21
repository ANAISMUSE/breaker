import pandas as pd
import numpy as np
from pathlib import Path

from src.config.settings import settings
from src.embedding.pipeline import build_semantic_vector_store
from src.evaluation.metrics_v2 import dataframe_embeddings_matrix


def test_build_semantic_vector_store() -> None:
    settings.llm_provider = "local"
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
    assert "embedding_fused" in enriched_df.columns
    assert "multimodal_evidence" in enriched_df.columns
    assert enriched_df.attrs.get("vector_schema_version") == "v2"
    assert enriched_df.attrs.get("multimodal_schema_version") == "mm_v1"
    snapshot_path = enriched_df.attrs.get("docarray_snapshot_path")
    if snapshot_path:
        assert Path(str(snapshot_path)).exists()
    first = store.metadata[0]
    assert first.get("multimodal_schema_version") == "mm_v1"
    assert isinstance(first.get("multimodal_evidence"), list)

    result = store.search(np.asarray(store.vectors[0], dtype=np.float32), top_k=1, vector_field="fused")
    assert len(result) == 1
    assert "fused" in result[0]["vector_bundle"]
    assert result[0]["metadata_version"] == "m2"

    hybrid = store.hybrid_search(
        {
            "fused": np.asarray(store.vectors[0], dtype=np.float32),
            "text": np.asarray(store.vector_bundles[0]["text"], dtype=np.float32),
        },
        top_k=1,
        field_weights={"fused": 0.7, "text": 0.3},
    )
    assert len(hybrid) == 1


def test_dataframe_embeddings_matrix_prefers_fused() -> None:
    fused = np.asarray([1.0, 2.0, 3.0], dtype=np.float32)
    plain = np.asarray([0.0, 0.0, 1.0], dtype=np.float32)
    df = pd.DataFrame([{"embedding": plain, "embedding_fused": fused}])
    matrix = dataframe_embeddings_matrix(df)
    assert matrix is not None
    assert matrix.shape == (1, 3)
    assert np.allclose(matrix[0], fused.astype(np.float64))
