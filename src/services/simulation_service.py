from __future__ import annotations

import pandas as pd

from src.simulation.strategies import compare_strategies
from src.twin.twin_builder import DigitalTwinProfile


class SimulationService:
    def compare(self, profile: DigitalTwinProfile, df: pd.DataFrame, benchmark: dict[str, float], rounds: int) -> dict:
        return compare_strategies(profile, df, benchmark, rounds=rounds, seed=42)

