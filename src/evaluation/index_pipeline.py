from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.evaluation.metrics import (
    cognitive_blindspot_score,
    content_diversity_score,
    cross_domain_exposure_score,
    polarization_risk_score,
)
from src.evaluation.metrics_v2 import (
    behavior_weights_for_df,
    cocoon_index_from_scores,
    dataframe_embeddings_matrix,
    score_s1_content_diversity,
    score_s2_cross_domain,
    score_s3_stance_diversity,
    score_s4_cognitive_coverage,
)


@dataclass
class EvaluationResult:
    """兼容旧版 0–100 风格展示（逐步迁移中）。"""

    content_diversity: float
    cross_domain_exposure: float
    polarization_risk: float
    cognitive_blindspot: float
    cocoon_index: float


@dataclass
class EvaluationResultV2:
    """PDF 3.6：四维多样性得分 S1–S4（1–10，越高越好）与茧房指数 C（0–10，越高越糟）。"""

    s1_content_diversity: float
    s2_cross_domain: float
    s3_stance_diversity: float
    s4_cognitive_coverage: float
    cocoon_index: float
    mode: str  # "static" | "dynamic"


def _distribution(series: pd.Series) -> dict[str, float]:
    cnt = series.value_counts(normalize=True)
    return {k: float(v) for k, v in cnt.to_dict().items()}


def evaluate_user_cocoon(df: pd.DataFrame, benchmark_dist: dict[str, float]) -> EvaluationResult:
    diversity = content_diversity_score(df["topic"].astype(str).tolist())
    cross = cross_domain_exposure_score(df["topic"].astype(str).tolist())
    polar = polarization_risk_score(df["stance"].astype(str).tolist(), df["emotion_score"].astype(float).tolist())
    user_dist = _distribution(df["topic"].astype(str))
    blindspot = cognitive_blindspot_score(user_dist, benchmark_dist)

    cocoon = (100 - diversity) * 0.25 + (100 - cross) * 0.25 + polar * 0.25 + blindspot * 0.25
    return EvaluationResult(
        content_diversity=round(diversity, 2),
        cross_domain_exposure=round(cross, 2),
        polarization_risk=round(polar, 2),
        cognitive_blindspot=round(blindspot, 2),
        cocoon_index=round(cocoon, 2),
    )


def evaluate_cocoon_pdf36(
    df: pd.DataFrame,
    benchmark_dist: dict[str, float],
    mode: str = "static",
) -> EvaluationResultV2:
    """静态或动态评估共用同一套公式；动态模式传入模拟产生的 df 即可。"""
    if df.empty:
        return EvaluationResultV2(1.0, 1.0, 1.0, 1.0, 10.0, mode=mode)
    weights = behavior_weights_for_df(df)
    emb = dataframe_embeddings_matrix(df)
    s1 = score_s1_content_diversity(df, weights)
    s2 = score_s2_cross_domain(df, weights, emb)
    s3 = score_s3_stance_diversity(df, weights)
    s4 = score_s4_cognitive_coverage(df, weights, benchmark_dist, emb)
    c = cocoon_index_from_scores(s1, s2, s3, s4)
    return EvaluationResultV2(
        s1_content_diversity=s1,
        s2_cross_domain=s2,
        s3_stance_diversity=s3,
        s4_cognitive_coverage=s4,
        cocoon_index=c,
        mode=mode,
    )


def evaluation_v2_to_legacy_display(ev: EvaluationResultV2) -> EvaluationResult:
    """雷达图等如需旧 0–100 刻度：将 1–10 线性映射到 10–100。"""
    scale = lambda x: round((float(x) - 1.0) / 9.0 * 100.0, 2)
    return EvaluationResult(
        content_diversity=scale(ev.s1_content_diversity),
        cross_domain_exposure=scale(ev.s2_cross_domain),
        polarization_risk=100.0 - scale(ev.s3_stance_diversity),
        cognitive_blindspot=100.0 - scale(ev.s4_cognitive_coverage),
        cocoon_index=round(float(ev.cocoon_index) * 10.0, 2),
    )
