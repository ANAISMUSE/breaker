from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd

from src.evaluation.index_pipeline import EvaluationResultV2, evaluate_cocoon_pdf36
from src.evaluation.metrics_v2 import dataframe_embeddings_matrix
from src.llm import get_llm_provider
from src.simulation.action_generation import (
    ACTION_TYPES,
    CandidateContent,
    roulette_choice,
    score_action_vector,
    softmax_zscores,
)
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
    llm_acceptance_shift: float = 0.0
    llm_preferred_action: str = ""


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


def _llm_acceptance_shift(candidate: CandidateContent, profile: DigitalTwinProfile, provider) -> float:
    """
    LLM 认知转移修正项（-0.2~0.2）：
    - 若候选内容位于高频主题邻域，提升接受度；
    - 若候选话题明显盲区，保持适中探索增益。
    """
    try:
        extraction = provider.extract_semantics(text=candidate.text_summary)
        topic = (extraction.topic or candidate.topic).lower()
    except Exception:
        topic = candidate.topic.lower()
    tw = {str(k).lower(): float(v) for k, v in profile.interest.topic_weights.items()}
    if not tw:
        return 0.0
    if topic in tw:
        return min(0.2, 0.05 + tw[topic] * 0.3)
    return 0.08


def _parse_round_adjustments(raw: object, sample_size: int) -> dict[int, dict]:
    out: dict[int, dict] = {}
    if not isinstance(raw, dict):
        return out
    items = raw.get("adjustments", [])
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        idx = int(item.get("idx", -1))
        if idx < 0 or idx >= sample_size:
            continue
        action_bias = item.get("action_bias", {})
        if not isinstance(action_bias, dict):
            action_bias = {}
        acceptance = float(item.get("acceptance_shift", 0.0) or 0.0)
        acceptance = float(min(0.25, max(-0.25, acceptance)))
        out[idx] = {
            "acceptance_shift": acceptance,
            "preferred_action": str(item.get("preferred_action", "")),
            "action_bias": {str(k): float(v) for k, v in action_bias.items() if str(k) in ACTION_TYPES},
        }
    return out


def _heuristic_round_adjustments(candidates: list[CandidateContent], profile: DigitalTwinProfile) -> dict[int, dict]:
    tw = {str(k).lower(): float(v) for k, v in profile.interest.topic_weights.items()}
    out: dict[int, dict] = {}
    for idx, item in enumerate(candidates):
        weight = tw.get(item.topic.lower(), 0.0)
        if weight >= 0.2:
            out[idx] = {
                "acceptance_shift": 0.12,
                "preferred_action": "like",
                "action_bias": {"like": 0.18, "skip": -0.12},
            }
        else:
            out[idx] = {
                "acceptance_shift": 0.05,
                "preferred_action": "search",
                "action_bias": {"search": 0.2, "skip": -0.05},
            }
    return out


def _llm_round_adjustments(
    *,
    candidates: list[CandidateContent],
    profile: DigitalTwinProfile,
    strategy: BreakoutStrategy,
    round_index: int,
    history: list[SimulationRoundResult],
    llm_enabled: bool = True,
) -> dict[int, dict]:
    if not llm_enabled:
        return _heuristic_round_adjustments(candidates, profile)
    provider = get_llm_provider()
    short_candidates = [
        {"idx": idx, "topic": c.topic, "stance": c.stance, "novelty": round(float(c.novelty_keywords), 3)}
        for idx, c in enumerate(candidates)
    ]
    prompt = (
        "你是认知转移模拟器。请严格输出JSON对象。"
        "字段为 adjustments(list)。每个元素字段: idx(int), acceptance_shift(-0.25~0.25),"
        " preferred_action(like|comment|search|like_comment|skip),"
        " action_bias(object, 可选键同动作，值在-0.3~0.3)。"
        f"\nstrategy={strategy.value}"
        f"\nround_index={round_index}"
        f"\nprofile_top_topics={profile.interest.top_topics[:4]}"
        f"\nrecent_cocoon_series={[round(x.cocoon.cocoon_index, 3) for x in history[-3:]]}"
        f"\ncandidates={short_candidates}"
    )
    try:
        result = provider.invoke_json(prompt=prompt, temperature=0.2, retry_on_parse_error=True)
        parsed = result.parsed_json if isinstance(result.parsed_json, (dict, list)) else None
        if isinstance(parsed, dict):
            structured = _parse_round_adjustments(parsed, len(candidates))
            if structured:
                return structured
    except Exception:
        pass
    return _heuristic_round_adjustments(candidates, profile)


def _sample_action_with_bias(
    candidate: CandidateContent,
    profile: DigitalTwinProfile,
    rng: np.random.Generator,
    action_bias: dict[str, float] | None = None,
) -> tuple[str, np.ndarray]:
    raw = score_action_vector(candidate, profile)
    probs = softmax_zscores(raw)
    action_bias = action_bias or {}
    if action_bias:
        boost = np.ones(len(ACTION_TYPES), dtype=np.float64)
        for idx, name in enumerate(ACTION_TYPES):
            delta = float(action_bias.get(name, 0.0))
            boost[idx] = np.exp(max(-1.0, min(1.0, delta)))
        probs = probs * boost
        probs = probs / (probs.sum() + 1e-12)
    idx = roulette_choice(probs, rng=rng)
    return ACTION_TYPES[idx], probs


def build_candidate_pool(
    profile: DigitalTwinProfile,
    strategy: BreakoutStrategy,
    rng: np.random.Generator,
    pool_size: int = 12,
    llm_enabled: bool = True,
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
    llm_enabled: bool = True,
) -> tuple[list[SimulationRoundResult], pd.DataFrame, EvaluationResultV2]:
    """多轮：每轮从候选池抽样内容→动作生成→拼接到历史→重算动态茧房指数。"""
    rng = rng or np.random.default_rng()
    hist_rows = base_df.to_dict(orient="records")
    series: list[SimulationRoundResult] = []
    static_ev = evaluate_cocoon_pdf36(base_df, benchmark_dist, mode="static")

    # Keep interactive compare responsive: only a small LLM budget per strategy,
    # then fallback to deterministic heuristics for remaining rounds.
    llm_round_budget = 3
    for r in range(rounds):
        pool = build_candidate_pool(profile, strategy, rng, pool_size=10, llm_enabled=llm_enabled)
        sampled = pool[:5]
        allow_llm_this_round = llm_enabled and r < llm_round_budget
        adjustments = _llm_round_adjustments(
            candidates=sampled,
            profile=profile,
            strategy=strategy,
            round_index=r,
            history=series,
            llm_enabled=allow_llm_this_round,
        )
        actions_count = {a: 0 for a in ACTION_TYPES}
        new_rows: list[dict] = []
        acceptance_total = 0.0
        preferred_actions: list[str] = []
        for idx, cand in enumerate(sampled):
            adj = adjustments.get(idx, {})
            acceptance_shift = float(adj.get("acceptance_shift", 0.0) or 0.0)
            if acceptance_shift:
                cand.novelty_keywords = float(min(1.0, max(0.0, cand.novelty_keywords + acceptance_shift)))
                cand.platform_engagement = float(min(1.0, max(0.0, cand.platform_engagement + acceptance_shift * 0.5)))
            acceptance_total += acceptance_shift
            preferred = str(adj.get("preferred_action", ""))
            if preferred:
                preferred_actions.append(preferred)
            action, _ = _sample_action_with_bias(
                cand,
                profile,
                rng=rng,
                action_bias=adj.get("action_bias", {}) if isinstance(adj, dict) else {},
            )
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
        dominant = max(preferred_actions, key=preferred_actions.count) if preferred_actions else ""
        series.append(
            SimulationRoundResult(
                round_index=r,
                cocoon=ev,
                actions_summary=actions_count,
                llm_acceptance_shift=acceptance_total / max(1, len(sampled)),
                llm_preferred_action=dominant,
            )
        )

    final_df = pd.DataFrame(hist_rows)
    final_ev = series[-1].cocoon if series else static_ev
    return series, final_df, final_ev


def compare_strategies(
    profile: DigitalTwinProfile,
    base_df: pd.DataFrame,
    benchmark_dist: dict[str, float],
    rounds: int = 10,
    seed: int = 42,
    llm_enabled: bool = True,
) -> dict[str, dict]:
    """对四套策略各跑一遍，返回茧房指数变化与最优策略名。"""
    rng_master = np.random.default_rng(seed)
    results: dict[str, dict] = {}
    static = evaluate_cocoon_pdf36(base_df, benchmark_dist, mode="static")
    llm_enhanced = dataframe_embeddings_matrix(base_df) is not None
    best_name = ""
    best_drop = -1e9
    llm_strategies = {BreakoutStrategy.ladder, BreakoutStrategy.mixed}
    for strat in BreakoutStrategy:
        rng = np.random.default_rng(int(rng_master.integers(0, 1_000_000)))
        llm_enabled_for_strategy = llm_enabled and strat in llm_strategies
        series, _, final_ev = run_strategy_simulation(
            profile,
            base_df,
            benchmark_dist,
            strat,
            rounds=rounds,
            rng=rng,
            llm_enabled=llm_enabled_for_strategy,
        )
        c0 = static.cocoon_index
        c1 = final_ev.cocoon_index
        drop = c0 - c1
        tail = [sr.cocoon.cocoon_index for sr in series]
        trajectory = [
            {
                "round": sr.round_index,
                "cocoon_index": round(float(sr.cocoon.cocoon_index), 4),
                "actions": sr.actions_summary,
                "llm_acceptance_shift": round(float(sr.llm_acceptance_shift), 4),
                "llm_preferred_action": sr.llm_preferred_action,
            }
            for sr in series
        ]
        results[strat.value] = {
            "cocoon_start": c0,
            "cocoon_end": c1,
            "drop": round(drop, 3),
            "series": [c0] + tail,
            "trajectory": trajectory,
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
