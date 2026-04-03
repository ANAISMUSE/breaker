import numpy as np
import pandas as pd

from src.evaluation.index_pipeline import evaluate_cocoon_pdf36


def test_evaluate_cocoon_pdf36_nonempty() -> None:
    df = pd.DataFrame(
        {
            "topic": ["a", "b", "a", "c"],
            "stance": ["neutral", "positive", "negative", "neutral"],
            "like": [1, 0, 5, 0],
            "comment": [0, 1, 0, 0],
            "share": [0, 0, 0, 0],
            "duration": [10, 20, 30, 5],
        }
    )
    bench = {"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}
    ev = evaluate_cocoon_pdf36(df, bench, mode="static")
    assert 1 <= ev.s1_content_diversity <= 10
    assert 0 <= ev.cocoon_index <= 10


def test_evaluate_cocoon_pdf36_with_embeddings() -> None:
    emb = np.random.randn(5, 4)
    df = pd.DataFrame(
        {
            "topic": list("abcde"),
            "stance": ["n"] * 5,
            "like": [0] * 5,
            "comment": [0] * 5,
            "share": [0] * 5,
            "duration": [1] * 5,
            "embedding": [emb[i] for i in range(5)],
        }
    )
    bench = {"a": 0.2, "b": 0.2, "c": 0.2, "d": 0.2, "e": 0.2}
    ev = evaluate_cocoon_pdf36(df, bench)
    assert ev.s4_cognitive_coverage >= 1
