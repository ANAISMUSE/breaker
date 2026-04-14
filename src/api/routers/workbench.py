from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

from src.agents.policies import generate_ladder_plan
from src.data_ingestion.schema import normalize_topic
from src.evaluation.index_pipeline import evaluate_cocoon_pdf36
from src.twin.twin_builder import ensure_profile_dataframe
from src.web.report_export import export_word_report

router = APIRouter(prefix="/workbench", tags=["workbench"])


class PlanIn(BaseModel):
    rows: list[dict]
    benchmark: dict[str, float]


class ReportIn(BaseModel):
    rows: list[dict]
    benchmark: dict[str, float]
    strategy_summary: Optional[str] = None
    platform_placeholder: Optional[str] = None


class TrainingStartIn(BaseModel):
    topic: str
    pro_view: str
    con_view: str


class TrainingSubmitIn(BaseModel):
    summary: str
    reflection: str = ""


def _training_path() -> Path:
    p = Path("data/cognitive_training_records.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text("[]", encoding="utf-8")
    return p


def _load_training_records() -> list[dict]:
    try:
        raw = json.loads(_training_path().read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else []
    except Exception:
        return []


def _save_training_records(rows: list[dict]) -> None:
    _training_path().write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


@router.post("/plan")
def plan(payload: PlanIn) -> dict:
    df = ensure_profile_dataframe(pd.DataFrame(payload.rows))
    if not df.empty:
        df["topic"] = df["topic"].astype(str).map(normalize_topic)
    ev = evaluate_cocoon_pdf36(df, payload.benchmark, mode="static")
    top_topics = df["topic"].astype(str).value_counts().index.tolist() if not df.empty else []
    ladder_plan = generate_ladder_plan(ev, top_topics)
    return {
        "evaluation": ev.__dict__,
        "ladder_plan": ladder_plan,
    }


@router.post("/report")
def report(payload: ReportIn) -> dict:
    df = ensure_profile_dataframe(pd.DataFrame(payload.rows))
    if not df.empty:
        df["topic"] = df["topic"].astype(str).map(normalize_topic)
    ev = evaluate_cocoon_pdf36(df, payload.benchmark, mode="static")
    top_topics = df["topic"].astype(str).value_counts().index.tolist() if not df.empty else []
    ladder_plan = generate_ladder_plan(ev, top_topics)
    out = export_word_report(
        result=ev,
        ladder_plan=ladder_plan,
        df=df,
        strategy_summary=payload.strategy_summary,
        platform_placeholder=payload.platform_placeholder,
    )
    return {"path": out, "evaluation": ev.__dict__, "ladder_plan": ladder_plan}


@router.post("/training/start")
def start_training(payload: TrainingStartIn) -> dict:
    rows = _load_training_records()
    rec = {
        "training_id": str(uuid.uuid4()),
        "topic": payload.topic.strip() or "general",
        "pro_view": payload.pro_view.strip(),
        "con_view": payload.con_view.strip(),
        "status": "started",
        "summary": "",
        "reflection": "",
        "score": 0.0,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    rows.insert(0, rec)
    _save_training_records(rows[:300])
    return rec


@router.post("/training/{training_id}/submit")
def submit_training(training_id: str, payload: TrainingSubmitIn) -> dict:
    rows = _load_training_records()
    out = None
    summary = payload.summary.strip()
    # Simple rubric: reward mentioning both sides and cross-domain reasoning words.
    score = 0.0
    if summary:
        score += 0.4
    if any(k in summary.lower() for k in ("但是", "同时", "另一方面", "however", "while", "同时也")):
        score += 0.3
    if payload.reflection.strip():
        score += 0.3
    score = round(min(1.0, score), 3)
    for i, rec in enumerate(rows):
        if str(rec.get("training_id")) != training_id:
            continue
        rec["status"] = "submitted"
        rec["summary"] = summary
        rec["reflection"] = payload.reflection.strip()
        rec["score"] = score
        rec["updated_at"] = datetime.utcnow().isoformat() + "Z"
        rows[i] = rec
        out = rec
        break
    if out is None:
        return {"error": "training not found"}
    _save_training_records(rows)
    return out


@router.get("/training/records")
def list_training_records(limit: int = 50) -> list[dict]:
    rows = _load_training_records()
    rows = sorted(rows, key=lambda x: str(x.get("updated_at", "")), reverse=True)
    return rows[: max(1, int(limit))]

