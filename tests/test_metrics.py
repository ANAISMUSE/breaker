import pandas as pd

from src.evaluation.index_pipeline import evaluate_user_cocoon


def test_evaluate_user_cocoon_returns_expected_range() -> None:
    df = pd.DataFrame(
        [
            {"topic": "technology", "stance": "neutral", "emotion_score": 3},
            {"topic": "entertainment", "stance": "neutral", "emotion_score": 2},
            {"topic": "society", "stance": "left", "emotion_score": 4},
        ]
    )
    benchmark = {"technology": 0.3, "entertainment": 0.3, "society": 0.4}
    result = evaluate_user_cocoon(df, benchmark)
    assert 0 <= result.cocoon_index <= 100
