from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd

from src.evaluation.index_pipeline import EvaluationResultV2, evaluate_cocoon_pdf36
from src.evaluation.metrics_v2 import dataframe_embeddings_matrix
from src.simulation.action_generation import ACTION_TYPES, CandidateContent, sample_user_action
from src.twin.twin_builder import DigitalTwinProfile


class BreakoutStrategy(str, Enum):
    baseline = "baseline"
    aggressive = "aggressive"
    ladder = "ladder"
    mixed = "mixed"


@dataclass
class SimulationRoundResult:
    round_index: int
    cocoon: EvaluationResultV2
    actions_summary: dict[str, int] = field(default_factory=dict)


def _synth_row_from_candidate(
    candidate: CandidateContent,
    action: str,
    platform: str = "sim",
) -> dict:
    """将单次模拟动作折叠为一行类行为记录，供评估复用。"""
    like = 1 if action == "like" or action == "like_comment" else 0
    comment = 1 if action in ("comment", "like_comment") else 0
    search_boost = 1 if action == "search" else 0
    duration = 5.0 if action == "skip" else 25.0 + search_boost * 10.0
    return {
        "user_id": "twin_sim",
        "platform": platform,
        "content_id": f"sim_{candidate.topic}_{hash(candidate.text_summary) % 10_000}",
        "timestamp": pd.Timestamp.utcnow(),
        "content_type": "sim",
        "text": candidate.text_summary,
        "image_url": "",
        "video_url": "",
        "like": like,
        "comment": comment,
        "share": 0,
        "duration": duration,
        "topic": candidate.topic,
        "stance": candidate.stance,
        "emotion_score": 3.0 + (0.5 - candidate.discussion_score),
        "author_id": "",
    }


def _can_broadcast_scalar_fill(val: object) -> bool:
    """仅用「可整列广播的标量」补列；向量列（如 embedding）否则会触发长度不匹配。"""
    if val is None:
        return True
    if isinstance(val, (str, bytes, bool, int, float, np.integer, np.floating)):
        return True
    if isinstance(val, pd.Timestamp):
        return True
    if isinstance(val, np.ndarray):
        return val.size == 1
    if isinstance(val, (list, tuple)):
        return len(val) <= 1
    return True


def build_candidate_pool(
    profile: DigitalTwinProfile,
    strategy: BreakoutStrategy,
    rng: np.random.Generator,
    pool_size: int = 12,
) -> list[CandidateContent]:
    """根据策略生成破茧内容候选池（简化：主题在核心/邻域/盲区间插值）。"""
    topics = list(profile.interest.topic_weights.keys()) or ["other"]
    top = profile.interest.top_topics or topics[:1]
    rare = [t for t in topics if t not in top] or ["society", "education"]
    out: list[CandidateContent] = []
    for i in range(pool_size):
        if strategy == BreakoutStrategy.baseline:
            t = top[rng.integers(0, len(top))]
            novelty = 0.2
        elif strategy == BreakoutStrategy.aggressive:
            t = rare[rng.integers(0, len(rare))]
            novelty = 0.9
        elif strategy == BreakoutStrategy.ladder:
            frac = i / max(pool_size - 1, 1)
            t = top[0] if frac < 0.35 else (top[min(1, len(top) - 1)] if frac < 0.7 else rare[rng.integers(0, len(rare))])
            novelty = 0.3 + 0.5 * frac
        else:
            t = top[rng.integers(0, len(top))] if rng.random() < 0.5 else rare[rng.integers(0, len(rare))]
            novelty = 0.45 + 0.2 * rng.random()
        stance_roll = rng.random()
        stance = "neutral"
        if stance_roll > 0.6:
            stance = "positive"
        elif stance_roll < 0.3:
            stance = "negative"
        out.append(
            CandidateContent(
                topic=t,
                stance=stance,
                text_summary=f"simulated item {i} on {t}",
                discussion_score=float(0.3 + 0.6 * rng.random()),
                novelty_keywords=float(novelty),
                platform_engagement=float(0.4 + 0.5 * rng.random()),
                comment_count_hint=float(0.2 + 0.6 * rng.random()),
                semantic_similarity=float(0.2 + 0.7 * rng.random()),
            )
        )
    return out


def run_strategy_simulation(
    profile: DigitalTwinProfile,
    base_df: pd.DataFrame,
    benchmark_dist: dict[str, float],
    strategy: BreakoutStrategy,
    rounds: int = 14,
    rng: np.random.Generator | None = None,
) -> tuple[list[SimulationRoundResult], pd.DataFrame, EvaluationResultV2]:
    """多轮：每轮从候选池抽样内容→动作生成→拼接到历史→重算动态茧房指数。"""
    rng = rng or np.random.default_rng()
    hist_rows = base_df.to_dict(orient="records")
    series: list[SimulationRoundResult] = []
    static_ev = evaluate_cocoon_pdf36(base_df, benchmark_dist, mode="static")

    for r in range(rounds):
        pool = build_candidate_pool(profile, strategy, rng, pool_size=10)
        actions_count = {a: 0 for a in ACTION_TYPES}
        new_rows: list[dict] = []
        for cand in pool[:5]:
            action, _, _ = sample_user_action(cand, profile, rng=rng)
            actions_count[action] = actions_count.get(action, 0) + 1
            row = _synth_row_from_candidate(cand, action)
            new_rows.append(row)
        hist_rows.extend(new_rows)
        sim_df = pd.DataFrame(hist_rows)
        if "embedding" in sim_df.columns:
            invalid = sim_df["embedding"].apply(lambda x: x is None or (isinstance(x, float) and pd.isna(x)))
            if invalid.any():
                sim_df = sim_df.drop(columns=["embedding"])
        for col in base_df.columns:
            if col not in sim_df.columns:
                val = base_df[col].iloc[0] if len(base_df) else None
                if col == "embedding" or not _can_broadcast_scalar_fill(val):
                    continue
                sim_df[col] = val
        ev = evaluate_cocoon_pdf36(sim_df, benchmark_dist, mode="dynamic")
        series.append(SimulationRoundResult(round_index=r, cocoon=ev, actions_summary=actions_count))

    final_df = pd.DataFrame(hist_rows)
    final_ev = series[-1].cocoon if series else static_ev
    return series, final_df, final_ev


def compare_strategies(
    profile: DigitalTwinProfile,
    base_df: pd.DataFrame,
    benchmark_dist: dict[str, float],
    rounds: int = 10,
    seed: int = 42,
) -> dict[str, dict]:
    """对四套策略各跑一遍，返回茧房指数变化与最优策略名。"""
    rng_master = np.random.default_rng(seed)
    results: dict[str, dict] = {}
    static = evaluate_cocoon_pdf36(base_df, benchmark_dist, mode="static")
    llm_enhanced = dataframe_embeddings_matrix(base_df) is not None
    best_name = ""
    best_drop = -1e9
    for strat in BreakoutStrategy:
        rng = np.random.default_rng(int(rng_master.integers(0, 1_000_000)))
        series, _, final_ev = run_strategy_simulation(
            profile, base_df, benchmark_dist, strat, rounds=rounds, rng=rng
        )
        c0 = static.cocoon_index
        c1 = final_ev.cocoon_index
        drop = c0 - c1
        tail = [sr.cocoon.cocoon_index for sr in series]
        results[strat.value] = {
            "cocoon_start": c0,
            "cocoon_end": c1,
            "drop": round(drop, 3),
            "series": [c0] + tail,
            "llm_enhanced": llm_enhanced,
            "explanation": _strategy_explanation(strat, drop=drop, llm_enhanced=llm_enhanced),
        }
        if drop > best_drop:
            best_drop = drop
            best_name = strat.value
    results["_best"] = {
        "name": best_name,
        "drop": round(best_drop, 3),
        "static_cocoon": static.cocoon_index,
        "reason": _strategy_explanation(BreakoutStrategy(best_name), drop=best_drop, llm_enhanced=llm_enhanced)
        if best_name
        else "",
    }
    return results


def _strategy_explanation(strategy: BreakoutStrategy, drop: float, llm_enhanced: bool) -> str:
    llm_note = "（含语义向量）" if llm_enhanced else "（仅主题/立场）"
    if strategy == BreakoutStrategy.ladder:
        return f"阶梯策略通过逐步提高新颖度来降低用户抵触，通常在稳定改善上更均衡{llm_note}。"
    if strategy == BreakoutStrategy.aggressive:
        return f"激进策略快速引入非头部主题，短期变化大但波动更高{llm_note}。"
    if strategy == BreakoutStrategy.mixed:
        return f"混合策略在核心兴趣与新主题间折中，适合中等强度干预{llm_note}。"
    if drop < 0:
        return f"基线策略可能加剧同温层沉浸，当前模拟显示改善不足{llm_note}。"
    return f"基线策略偏向保持现有偏好，改善幅度通常最保守{llm_note}。"
