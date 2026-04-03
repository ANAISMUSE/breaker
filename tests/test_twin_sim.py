import numpy as np
import pandas as pd

from src.simulation.action_generation import sample_user_action, CandidateContent
from src.simulation.strategies import BreakoutStrategy, compare_strategies
from src.twin.twin_builder import build_digital_twin_profile


def test_twin_and_action_sample() -> None:
    df = pd.DataFrame(
        {
            "content_id": ["1", "2"],
            "timestamp": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "text": ["a", "b"],
            "topic": ["tech", "society"],
            "stance": ["neutral", "positive"],
            "like": [1, 0],
            "comment": [0, 1],
            "share": [0, 0],
            "duration": [10, 20],
            "emotion_score": [3, 3],
            "embedding": [np.ones(4), np.ones(4) * 0.5],
        }
    )
    p = build_digital_twin_profile(df)
    assert p.interest.topic_weights
    c = CandidateContent(topic="tech", stance="neutral", text_summary="x")
    action, raw, probs = sample_user_action(c, p, rng=np.random.default_rng(0))
    assert action in {"like", "comment", "search", "like_comment", "skip"}
    assert len(raw) == 5 and abs(probs.sum() - 1.0) < 1e-5


def test_compare_strategies_runs() -> None:
    df = pd.DataFrame(
        {
            "user_id": ["u", "u", "u"],
            "platform": ["douyin", "douyin", "douyin"],
            "content_id": ["1", "2", "3"],
            "timestamp": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
            "content_type": ["v", "v", "v"],
            "text": ["a", "b", "c"],
            "image_url": ["", "", ""],
            "video_url": ["", "", ""],
            "like": [1, 0, 0],
            "comment": [0, 0, 0],
            "share": [0, 0, 0],
            "duration": [5, 5, 5],
            "topic": ["a", "b", "c"],
            "stance": ["n", "n", "p"],
            "emotion_score": [3, 3, 3],
            "author_id": ["", "", ""],
        }
    )
    bench = {"a": 0.34, "b": 0.33, "c": 0.33}
    profile = build_digital_twin_profile(df)
    out = compare_strategies(profile, df, bench, rounds=3, seed=1)
    assert "_best" in out
    assert BreakoutStrategy.baseline.value in out
