from __future__ import annotations

import pandas as pd

from src.evaluation.index_pipeline import evaluate_cocoon_pdf36


def run_eval_node(state: dict) -> dict:
    df: pd.DataFrame = state.get("df", pd.DataFrame())
    benchmark = state.get("benchmark", {})
    result = evaluate_cocoon_pdf36(df, benchmark, mode="static")
    state["evaluation_result"] = result
    state.setdefault("trace", []).append({"node": "eval", "cocoon_index": float(result.cocoon_index)})
    return state
