from __future__ import annotations

from typing import Union

from src.evaluation.index_pipeline import EvaluationResult, EvaluationResultV2


def generate_ladder_plan(result: Union[EvaluationResult, EvaluationResultV2], top_topics: list[str]) -> list[dict]:
    base = top_topics[0] if top_topics else "entertainment"
    expand = top_topics[1] if len(top_topics) > 1 else "technology"
    challenge = "society" if base != "society" else "education"

    plan = [
        {
            "level": "L1 轻微扩展",
            "topic": f"{base} + {expand}",
            "reason": "在现有兴趣邻域内引入相邻主题，降低心理抵触。",
        },
        {
            "level": "L2 中等扩展",
            "topic": f"{expand} + health",
            "reason": "引入跨生活场景的信息，提升跨域曝光率。",
        },
        {
            "level": "L3 认知挑战",
            "topic": challenge,
            "reason": "针对盲区和极化风险，加入温和但多元的观点内容。",
        },
    ]

    if isinstance(result, EvaluationResult):
        polar_high = result.polarization_risk > 70
    else:
        polar_high = result.s3_stance_diversity < 4.0
    if polar_high:
        plan[2]["reason"] += " 当前立场多样性偏低，优先推荐多立场对照内容。"
    return plan
