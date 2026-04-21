from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import require_roles
from src.agents.policies import generate_ladder_plan
from src.config.settings import settings
from src.data_ingestion.schema import normalize_topic
from src.evaluation.index_pipeline import evaluate_cocoon_pdf36
from src.llm import get_llm_provider
from src.training.phase5_pipeline import run_phase5_pipeline
from src.twin.twin_builder import ensure_profile_dataframe
from src.web.report_export import export_word_report

router = APIRouter(prefix="/workbench", tags=["workbench"], dependencies=[Depends(require_roles(["admin"]))])


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


class TrainingMessageIn(BaseModel):
    role: str
    content: str


class Phase5RunIn(BaseModel):
    source_path: Optional[str] = None
    source_rows: Optional[list[dict]] = None
    workdir: str = "outputs/phase5_ui"
    baseline_model: Optional[str] = None
    lora_model: Optional[str] = None
    train_ratio: float = 0.8
    val_ratio: float = 0.1
    seed: int = 42
    skip_train: bool = True


def _training_path() -> Path:
    p = Path("data/cognitive_training_records.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text("[]", encoding="utf-8")
    return p


def _phase5_source_path() -> Path:
    p = Path("data/phase5_sources")
    p.mkdir(parents=True, exist_ok=True)
    return p / f"phase5_source_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.json"


def _write_phase5_source_rows(rows: list[dict]) -> str:
    if len(rows) < 20:
        raise ValueError("phase5 source_rows requires at least 20 samples")
    source_path = _phase5_source_path()
    source_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(source_path)


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
        "feedback": "",
        "evidence": [],
        "messages": [],
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
    score = 0.0
    feedback = ""
    evidence: list[str] = []
    for i, rec in enumerate(rows):
        if str(rec.get("training_id")) != training_id:
            continue
        topic = str(rec.get("topic", "general"))
        pro_view = str(rec.get("pro_view", ""))
        con_view = str(rec.get("con_view", ""))
        review = get_llm_provider().review_training_submission(
            topic=topic,
            pro_view=pro_view,
            con_view=con_view,
            summary=summary,
            reflection=payload.reflection.strip(),
        )
        score = float(review.score)
        feedback = str(review.feedback)
        evidence = [str(x) for x in review.evidence]
        rec["status"] = "submitted"
        rec["summary"] = summary
        rec["reflection"] = payload.reflection.strip()
        rec["score"] = score
        rec["feedback"] = feedback
        rec["evidence"] = evidence
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


@router.post("/training/{training_id}/message")
def append_training_message(training_id: str, payload: TrainingMessageIn) -> dict:
    rows = _load_training_records()
    out = None
    for i, rec in enumerate(rows):
        if str(rec.get("training_id")) != training_id:
            continue
        messages = rec.get("messages", [])
        if not isinstance(messages, list):
            messages = []
        messages.append(
            {
                "role": payload.role.strip() or "user",
                "content": payload.content.strip(),
                "ts": datetime.utcnow().isoformat() + "Z",
            }
        )
        rec["messages"] = messages[-50:]
        rec["updated_at"] = datetime.utcnow().isoformat() + "Z"
        rows[i] = rec
        out = rec
        break
    if out is None:
        return {"error": "training not found"}
    _save_training_records(rows)
    return out


@router.post("/phase5/run")
def run_phase5(payload: Phase5RunIn) -> dict:
    source_path = (payload.source_path or "").strip()
    if not source_path:
        if payload.source_rows:
            try:
                source_path = _write_phase5_source_rows(payload.source_rows)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        else:
            raise HTTPException(status_code=400, detail="Either source_path or source_rows must be provided.")
    baseline_model = (payload.baseline_model or "").strip() or settings.lora_base_model
    lora_model = (payload.lora_model or "").strip() or settings.active_local_chat_model()
    try:
        result = run_phase5_pipeline(
            source=source_path,
            workdir=payload.workdir.strip() or "outputs/phase5_ui",
            baseline_model=baseline_model,
            lora_model=lora_model,
            train_ratio=float(payload.train_ratio),
            val_ratio=float(payload.val_ratio),
            seed=int(payload.seed),
            skip_train=bool(payload.skip_train),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"phase5 pipeline failed: {exc}") from exc
    return {
        "ok": True,
        "source_path": source_path,
        "baseline_model": baseline_model,
        "lora_model": lora_model,
        "skip_train": bool(payload.skip_train),
        **result,
    }

