from __future__ import annotations

import json
from typing import Union

from src.evaluation.index_pipeline import EvaluationResult, EvaluationResultV2
from src.llm import get_llm_provider


def _default_plan(
    result: Union[EvaluationResult, EvaluationResultV2],
    top_topics: list[str],
    blindspots: list[str],
) -> list[dict]:
    base = top_topics[0] if top_topics else "entertainment"
    expand = top_topics[1] if len(top_topics) > 1 else "technology"
    challenge = blindspots[0] if blindspots else ("society" if base != "society" else "education")
    plan = [
        {
            "level": "L1 轻微扩展",
            "topic": f"{base} + {expand}",
            "reason": "在现有兴趣邻域内引入相邻主题，降低心理抵触。",
            "confidence": 0.7,
        },
        {
            "level": "L2 中等扩展",
            "topic": f"{expand} + health",
            "reason": "引入跨生活场景的信息，提升跨域曝光率。",
            "confidence": 0.65,
        },
        {
            "level": "L3 认知挑战",
            "topic": challenge,
            "reason": "针对盲区和极化风险，加入温和但多元的观点内容。",
            "confidence": 0.6,
        },
    ]
    if isinstance(result, EvaluationResult):
        polar_high = result.polarization_risk > 70
    else:
        polar_high = result.s3_stance_diversity < 4.0
    if polar_high:
        plan[2]["reason"] += " 当前立场多样性偏低，优先推荐多立场对照内容。"
    return plan


def _guess_blindspots(top_topics: list[str]) -> list[str]:
    candidates = ["history", "society", "health", "finance", "education", "culture", "science"]
    top = {t.lower() for t in top_topics}
    return [x for x in candidates if x not in top][:4]


def _trim_text(value: str, max_len: int = 160) -> str:
    cleaned = " ".join(value.split())
    return cleaned[:max_len]


def _serialize_history_note(prefix: str, payload: object, max_len: int = 260) -> str:
    try:
        raw = json.dumps(payload, ensure_ascii=False)
    except Exception:
        raw = str(payload)
    return f"{prefix}={_trim_text(raw, max_len=max_len)}"


def generate_ladder_plan(
    result: Union[EvaluationResult, EvaluationResultV2],
    top_topics: list[str],
    *,
    blindspots: list[str] | None = None,
    interest_topology: dict | None = None,
    history_feedback: list[str] | None = None,
) -> list[dict]:
    blindspots = blindspots or _guess_blindspots(top_topics)
    notes = []
    if isinstance(result, EvaluationResultV2):
        notes.append(f"cocoon_index={result.cocoon_index}")
        notes.append(f"scores={result.s1_content_diversity},{result.s2_cross_domain},{result.s3_stance_diversity},{result.s4_cognitive_coverage}")
    else:
        notes.append(f"cocoon_index={result.cocoon_index}")
        notes.append(f"polarization_risk={result.polarization_risk}")
    if interest_topology:
        notes.append(_serialize_history_note("interest_topology", interest_topology))
    if history_feedback:
        notes.extend(_trim_text(x, max_len=180) for x in history_feedback[:6] if str(x).strip())
    try:
        llm_plan = get_llm_provider().generate_strategy_plan(
            blindspots=blindspots,
            top_topics=top_topics[:6],
            history_notes=notes[:20],
        )
        normalized = []
        for item in llm_plan:
            normalized.append(
                {
                    "level": item.level,
                    "topic": item.topic,
                    "reason": item.reason,
                    "confidence": item.confidence,
                }
            )
        if normalized:
            return normalized
    except Exception:
        pass
    return _default_plan(result, top_topics, blindspots)
