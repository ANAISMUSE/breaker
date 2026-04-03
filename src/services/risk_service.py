from __future__ import annotations

import pandas as pd

from src.evaluation.index_pipeline import EvaluationResultV2, evaluate_cocoon_pdf36


class RiskService:
    def evaluate_overview(self, df: pd.DataFrame, benchmark: dict[str, float]) -> EvaluationResultV2:
        return evaluate_cocoon_pdf36(df, benchmark, mode="static")

