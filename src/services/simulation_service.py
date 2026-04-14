from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.simulation.strategies import compare_strategies
from src.storage.mysql_store import MySqlStore
from src.twin.twin_builder import DigitalTwinProfile


@dataclass
class SimulationRecord:
    record_id: str
    user_id: str
    rounds: int
    benchmark: dict[str, Any]
    result: dict[str, Any]
    rows: list[dict[str, Any]]
    created_at: str


class SimulationService:
    def __init__(self) -> None:
        self.mysql = MySqlStore.from_settings() if MySqlStore.enabled() else None

    def compare(self, profile: DigitalTwinProfile, df: pd.DataFrame, benchmark: dict[str, float], rounds: int) -> dict:
        result = compare_strategies(profile, df, benchmark, rounds=rounds, seed=42)
        best = result.get("_best", {}) if isinstance(result.get("_best", {}), dict) else {}
        result["_meta"] = {
            "best_strategy": best.get("name", ""),
            "best_reason": best.get("reason", ""),
        }
        return result

    def _path(self) -> Path:
        p = Path("data/simulation_records.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text("[]", encoding="utf-8")
        return p

    def _load(self) -> list[SimulationRecord]:
        rows = json.loads(self._path().read_text(encoding="utf-8"))
        out: list[SimulationRecord] = []
        for r in rows:
            out.append(
                SimulationRecord(
                    record_id=str(r.get("record_id", "")),
                    user_id=str(r.get("user_id", "unknown")),
                    rounds=int(r.get("rounds", 10)),
                    benchmark=r.get("benchmark", {}) if isinstance(r.get("benchmark", {}), dict) else {},
                    result=r.get("result", {}) if isinstance(r.get("result", {}), dict) else {},
                    rows=r.get("rows", []) if isinstance(r.get("rows", []), list) else [],
                    created_at=str(r.get("created_at", datetime.utcnow().isoformat() + "Z")),
                )
            )
        return out

    def _save(self, rows: list[SimulationRecord]) -> None:
        payload = [asdict(x) for x in rows]
        self._path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_record(
        self,
        user_id: str,
        rounds: int,
        benchmark: dict[str, Any],
        result: dict[str, Any],
        rows: list[dict[str, Any]],
    ) -> SimulationRecord:
        record = SimulationRecord(
            record_id=str(uuid.uuid4()),
            user_id=user_id or "unknown",
            rounds=int(rounds),
            benchmark=benchmark if isinstance(benchmark, dict) else {},
            result=result if isinstance(result, dict) else {},
            rows=rows if isinstance(rows, list) else [],
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        if self.mysql:
            self.mysql.create_simulation_record(
                record_id=record.record_id,
                user_id=record.user_id,
                rounds=record.rounds,
                benchmark=record.benchmark,
                result={**record.result, "_rows": record.rows},
            )
            return record

        records = self._load()
        records.insert(0, record)
        self._save(records[:200])
        return record

    def list_records(self, limit: int = 50) -> list[SimulationRecord]:
        cap = max(1, int(limit))
        if self.mysql:
            rows = self.mysql.list_simulation_records(limit=cap)
            out: list[SimulationRecord] = []
            for r in rows:
                result = r.get("result", {}) if isinstance(r.get("result", {}), dict) else {}
                payload_rows = result.get("_rows", [])
                if "_rows" in result:
                    result = {k: v for k, v in result.items() if k != "_rows"}
                out.append(
                    SimulationRecord(
                        record_id=str(r.get("record_id", "")),
                        user_id=str(r.get("user_id", "unknown")),
                        rounds=int(r.get("rounds", 10)),
                        benchmark=r.get("benchmark", {}) if isinstance(r.get("benchmark", {}), dict) else {},
                        result=result,
                        rows=payload_rows if isinstance(payload_rows, list) else [],
                        created_at=str(r.get("created_at", datetime.utcnow().isoformat() + "Z")),
                    )
                )
            return out

        records = sorted(self._load(), key=lambda x: x.created_at, reverse=True)
        return records[:cap]

