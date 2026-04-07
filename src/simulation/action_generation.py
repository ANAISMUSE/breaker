from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.twin.twin_builder import DigitalTwinProfile


ACTION_TYPES = ("like", "comment", "search", "like_comment", "skip")


@dataclass
class CandidateContent:
    """待模拟的破茧内容（可与真实推送或策略池条目对应）。"""

    topic: str
    stance: str
    text_summary: str
    discussion_score: float = 0.5
    novelty_keywords: float = 0.5
    platform_engagement: float = 0.5
    comment_count_hint: float = 0.3


def _topic_match_strength(profile: DigitalTwinProfile, topic: str) -> float:
    tw = profile.interest.topic_weights
    if not tw:
        return 0.5
    return float(min(1.0, tw.get(topic, 0.0) * len(tw)))


def _stance_distance(profile: DigitalTwinProfile, stance: str) -> float:
    sw = profile.cognitive.stance_weights
    if not sw:
        return 0.5
    dom = max(sw.values()) if sw else 0
    cur = sw.get(stance, 0.0)
    return float(min(1.0, 1.0 - abs(cur - dom)))


def score_action_vector(candidate: CandidateContent, profile: DigitalTwinProfile) -> np.ndarray:
    """5 个评估器原始得分（点赞/评论/搜索/赞评/跳过）。"""
    match_core = _topic_match_strength(profile, candidate.topic)
    engage = candidate.platform_engagement
    discuss = candidate.discussion_score
    novelty = candidate.novelty_keywords
    low_comments = 1.0 - min(1.0, candidate.comment_count_hint)
    fatigue_like = profile.behavior.like_rate * 0.4
    fatigue_deep = (profile.behavior.like_rate + profile.behavior.comment_rate) * 0.25

    s_like = match_core * 0.55 + engage * 0.35 - fatigue_like
    s_comment = discuss * 0.45 + _stance_distance(profile, candidate.stance) * 0.35 + engage * 0.2 - fatigue_deep * 0.1
    s_comment += (1.0 - candidate.comment_count_hint) * 0.15
    s_search = novelty * 0.5 + (1.0 - match_core) * 0.25 + profile.cognitive.polarization_hint * 0.15
    s_search += (1.0 - engage) * 0.1
    s_both = match_core * discuss * 0.55 + (profile.behavior.comment_rate + 0.1) * 0.35 - fatigue_deep * 0.5
    s_skip = (1.0 - match_core) * 0.45 + (1.0 - novelty) * 0.2 + low_comments * 0.2
    s_skip += (1.0 - profile.behavior.like_rate) * 0.15

    tr = profile.agent_traits
    s_like += tr.echo_delta * match_core + tr.shallow_like_delta
    s_comment += tr.deep_social_delta
    s_search += tr.explore_delta
    s_both += tr.deep_social_delta * 0.35
    s_skip += tr.skip_unfamiliar_delta * (1.0 - match_core)

    raw = np.array([s_like, s_comment, s_search, s_both, s_skip], dtype=np.float64)
    return raw


def softmax_zscores(raw: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    """Z-score 标准化后 Softmax 得概率分布。"""
    if raw.size == 0:
        return raw
    mu = raw.mean()
    sigma = raw.std() + 1e-6
    z = (raw - mu) / sigma
    z = z / max(temperature, 1e-6)
    ex = np.exp(z - np.max(z))
    return ex / (ex.sum() + 1e-12)


def roulette_choice(probs: np.ndarray, rng: np.random.Generator | None = None) -> int:
    rng = rng or np.random.default_rng()
    r = rng.random()
    cdf = np.cumsum(probs)
    return int(np.searchsorted(cdf, r))


def sample_user_action(
    candidate: CandidateContent,
    profile: DigitalTwinProfile,
    rng: np.random.Generator | None = None,
) -> tuple[str, np.ndarray, np.ndarray]:
    """返回 (动作名, 原始得分向量, 概率向量)。"""
    raw = score_action_vector(candidate, profile)
    probs = softmax_zscores(raw)
    idx = roulette_choice(probs, rng=rng)
    return ACTION_TYPES[idx], raw, probs
