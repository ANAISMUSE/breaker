from __future__ import annotations

import pandas as pd

from src.agents.state_protocol import AgentState, clamp_confidence, error_event, trace_event
from src.config.settings import settings
from src.simulation.strategies import compare_strategies
from src.twin.twin_builder import build_digital_twin_profile


def run_simulate_node(state: AgentState) -> dict:
    df: pd.DataFrame = state.get("df", pd.DataFrame())
    benchmark = state.get("benchmark", {})
    rounds = max(1, min(50, int(state.get("sim_rounds", 6) or 6)))
    if df.empty:
        return {
            "simulation_compare": {},
            "trace": [
                trace_event(
                    agent="simulateAgent",
                    status="degraded",
                    input_summary={"rows": 0},
                    output_summary={"best_strategy": "", "best_drop": 0.0},
                    fallback="skip simulation when dataframe is empty",
                )
            ],
            "confidence": {"simulateAgent": 0.2},
        }

    try:
        profile = build_digital_twin_profile(df)
        comparison = compare_strategies(
            profile,
            df,
            benchmark if isinstance(benchmark, dict) else {},
            rounds=rounds,
            seed=7,
            llm_enabled=bool(settings.use_llm_scoring),
        )
        best = comparison.get("_best", {}) if isinstance(comparison.get("_best", {}), dict) else {}
        best_drop = float(best.get("drop", 0.0) or 0.0)
        confidence = clamp_confidence(0.6 + min(0.3, best_drop))
        return {
            "simulation_compare": comparison,
            "trace": [
                trace_event(
                    agent="simulateAgent",
                    status="ok",
                    input_summary={"rows": int(len(df)), "rounds": rounds},
                    output_summary={"best_strategy": str(best.get("name", "")), "best_drop": best_drop},
                )
            ],
            "confidence": {"simulateAgent": confidence},
        }
    except Exception as exc:
        return {
            "simulation_compare": {},
            "trace": [
                trace_event(
                    agent="simulateAgent",
                    status="degraded",
                    input_summary={"rows": int(len(df))},
                    output_summary={"best_strategy": "", "best_drop": 0.0},
                    fallback="return empty simulation comparison",
                )
            ],
            "errors": [error_event(agent="simulateAgent", error=exc, fallback="return empty simulation comparison")],
            "confidence": {"simulateAgent": 0.0},
        }

