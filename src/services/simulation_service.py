from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from src.agents.policies import generate_ladder_plan
from src.config.settings import settings
from src.evaluation.index_pipeline import evaluate_cocoon_pdf36
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


@dataclass
class LadderExecutionRecord:
    execution_id: str
    user_id: str
    benchmark: dict[str, Any]
    plan_steps: list[dict[str, Any]]
    current_step_index: int
    status: str
    history: list[dict[str, Any]]
    rows: list[dict[str, Any]]
    created_at: str
    updated_at: str


class SimulationService:
    def __init__(self) -> None:
        self.mysql = MySqlStore.from_settings() if MySqlStore.enabled() else None

    def compare(
        self,
        profile: DigitalTwinProfile,
        df: pd.DataFrame,
        benchmark: dict[str, float],
        rounds: int,
        llm_enabled: bool = False,
    ) -> dict:
        result = compare_strategies(
            profile,
            df,
            benchmark,
            rounds=rounds,
            seed=42,
            llm_enabled=bool(settings.use_llm_scoring and llm_enabled),
        )
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

    def _ladder_path(self) -> Path:
        p = Path("data/ladder_executions.json")
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

    def _load_ladders(self) -> list[LadderExecutionRecord]:
        rows = json.loads(self._ladder_path().read_text(encoding="utf-8"))
        out: list[LadderExecutionRecord] = []
        for r in rows:
            out.append(
                LadderExecutionRecord(
                    execution_id=str(r.get("execution_id", "")),
                    user_id=str(r.get("user_id", "unknown")),
                    benchmark=r.get("benchmark", {}) if isinstance(r.get("benchmark", {}), dict) else {},
                    plan_steps=r.get("plan_steps", []) if isinstance(r.get("plan_steps", []), list) else [],
                    current_step_index=int(r.get("current_step_index", 0)),
                    status=str(r.get("status", "pending")),
                    history=r.get("history", []) if isinstance(r.get("history", []), list) else [],
                    rows=r.get("rows", []) if isinstance(r.get("rows", []), list) else [],
                    created_at=str(r.get("created_at", datetime.utcnow().isoformat() + "Z")),
                    updated_at=str(r.get("updated_at", datetime.utcnow().isoformat() + "Z")),
                )
            )
        return out

    def _save_ladders(self, rows: list[LadderExecutionRecord]) -> None:
        payload = [asdict(x) for x in rows]
        self._ladder_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

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

    def create_ladder_execution(
        self,
        user_id: str,
        rows: list[dict[str, Any]],
        benchmark: dict[str, Any],
    ) -> LadderExecutionRecord:
        df = pd.DataFrame(rows)
        ev = evaluate_cocoon_pdf36(df, benchmark if isinstance(benchmark, dict) else {}, mode="static")
        top_topics = df["topic"].astype(str).value_counts().index.tolist() if (not df.empty and "topic" in df.columns) else []
        plan_steps = generate_ladder_plan(ev, top_topics)
        now = datetime.utcnow().isoformat() + "Z"
        record = LadderExecutionRecord(
            execution_id=str(uuid.uuid4()),
            user_id=user_id or "unknown",
            benchmark=benchmark if isinstance(benchmark, dict) else {},
            plan_steps=plan_steps,
            current_step_index=0,
            status="planned",
            history=[],
            rows=rows if isinstance(rows, list) else [],
            created_at=now,
            updated_at=now,
        )
        rows_data = self._load_ladders()
        rows_data.insert(0, record)
        self._save_ladders(rows_data[:200])
        return record

    def list_ladder_executions(self, limit: int = 50) -> list[LadderExecutionRecord]:
        cap = max(1, int(limit))
        return sorted(self._load_ladders(), key=lambda x: x.updated_at, reverse=True)[:cap]

    def get_ladder_execution(self, execution_id: str) -> LadderExecutionRecord | None:
        for row in self._load_ladders():
            if row.execution_id == execution_id:
                return row
        return None

    def _update_ladder(
        self, execution_id: str, updater: Callable[[LadderExecutionRecord], LadderExecutionRecord]
    ) -> LadderExecutionRecord | None:
        rows = self._load_ladders()
        found = None
        for i, rec in enumerate(rows):
            if rec.execution_id == execution_id:
                found = updater(rec)
                rows[i] = found
                break
        if found is None:
            return None
        self._save_ladders(rows)
        return found

    def execute_ladder_step(self, execution_id: str) -> LadderExecutionRecord | None:
        def _apply(rec: LadderExecutionRecord) -> LadderExecutionRecord:
            idx = rec.current_step_index
            if idx >= len(rec.plan_steps):
                rec.status = "completed"
                rec.updated_at = datetime.utcnow().isoformat() + "Z"
                return rec
            step = rec.plan_steps[idx]
            rec.history.append(
                {
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "event": "execute_step",
                    "step_index": idx,
                    "step": step,
                }
            )
            rec.status = "running"
            rec.updated_at = datetime.utcnow().isoformat() + "Z"
            return rec

        return self._update_ladder(execution_id, _apply)

    def append_ladder_feedback(self, execution_id: str, score: float, note: str) -> LadderExecutionRecord | None:
        def _apply(rec: LadderExecutionRecord) -> LadderExecutionRecord:
            rec.history.append(
                {
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "event": "feedback",
                    "step_index": rec.current_step_index,
                    "score": float(score),
                    "note": note,
                }
            )
            rec.updated_at = datetime.utcnow().isoformat() + "Z"
            return rec

        return self._update_ladder(execution_id, _apply)

    def move_ladder_next(self, execution_id: str) -> LadderExecutionRecord | None:
        def _apply(rec: LadderExecutionRecord) -> LadderExecutionRecord:
            rec.current_step_index = min(rec.current_step_index + 1, len(rec.plan_steps))
            rec.status = "completed" if rec.current_step_index >= len(rec.plan_steps) else "running"
            rec.history.append(
                {
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "event": "next_step",
                    "step_index": rec.current_step_index,
                }
            )
            rec.updated_at = datetime.utcnow().isoformat() + "Z"
            return rec

        return self._update_ladder(execution_id, _apply)

