from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from src.evaluation.metrics_v2 import behavior_weight_row, kmeans_labels
from src.twin.memory import MemoryItem, build_memory_stream, stratified_memory_sample

_PROFILE_DEFAULTS: dict[str, object] = {
    "topic": "other",
    "stance": "neutral",
    "like": 0,
    "comment": 0,
    "share": 0,
    "duration": 0.0,
    "emotion_score": 3.0,
}


@dataclass(frozen=True)
class AgentBehaviorTraits:
    """与 `action_generation.score_action_vector` 协同的人设维度，用于差异化信息茧房/破茧模拟。"""

    key: str
    display_name: str
    summary: str
    explore_delta: float = 0.0
    echo_delta: float = 0.0
    shallow_like_delta: float = 0.0
    deep_social_delta: float = 0.0
    skip_unfamiliar_delta: float = 0.0


NEUTRAL_TRAITS = AgentBehaviorTraits(
    key="custom",
    display_name="自定义（数据驱动）",
    summary="未选择预设时，动作模拟仅由左侧行为统计与记忆流驱动；接入真实导出数据时请用此模式。",
)

ARCHETYPE_REGISTRY: dict[str, AgentBehaviorTraits] = {
    "elderly": AgentBehaviorTraits(
        key="elderly",
        display_name="老年人画像",
        summary="更依赖熟悉话题与主流立场，主动搜索弱、略倾向跳过陌生内容，适合评估「习惯推送」下的茧房风险。",
        explore_delta=-0.22,
        echo_delta=0.28,
        shallow_like_delta=0.12,
        deep_social_delta=0.02,
        skip_unfamiliar_delta=0.18,
    ),
    "youth": AgentBehaviorTraits(
        key="youth",
        display_name="青壮年画像",
        summary="互动深、愿参与讨论，对异质内容探索介于中间，适合作为一般对照人群。",
        explore_delta=0.12,
        echo_delta=0.06,
        shallow_like_delta=0.06,
        deep_social_delta=0.15,
        skip_unfamiliar_delta=-0.08,
    ),
    "child": AgentBehaviorTraits(
        key="child",
        display_name="少年儿童画像",
        summary="偏娱乐与轻互动、深度评论弱，易被强刺激内容留住，用于观察低龄向推荐与话题窄化。",
        explore_delta=0.06,
        echo_delta=0.14,
        shallow_like_delta=0.18,
        deep_social_delta=-0.12,
        skip_unfamiliar_delta=0.14,
    ),
    "explore_heavy": AgentBehaviorTraits(
        key="explore_heavy",
        display_name="高探索（低茧房倾向）",
        summary="主动搜索与跳出舒适区权重更高，可作破茧策略或对照组基线。",
        explore_delta=0.28,
        echo_delta=-0.1,
        shallow_like_delta=-0.05,
        deep_social_delta=0.12,
        skip_unfamiliar_delta=-0.2,
    ),
}

_PRESET_ALIASES: dict[str, str] = {
    "senior": "elderly",
    "老人": "elderly",
    "老年": "elderly",
    "老年人": "elderly",
    "young": "youth",
    "青年": "youth",
    "年轻人": "youth",
    "青壮年": "youth",
    "kid": "child",
    "少儿": "child",
    "儿童": "child",
    "小孩": "child",
    "少年": "child",
    "explore": "explore_heavy",
    "高探索": "explore_heavy",
    "破茧": "explore_heavy",
}


def resolve_agent_traits(df: pd.DataFrame) -> AgentBehaviorTraits:
    if df.empty or "persona_preset" not in df.columns:
        return NEUTRAL_TRAITS
    raw = df["persona_preset"].iloc[0]
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return NEUTRAL_TRAITS
    s = str(raw).strip()
    if not s:
        return NEUTRAL_TRAITS
    key = _PRESET_ALIASES.get(s) or _PRESET_ALIASES.get(s.lower()) or s.lower()
    return ARCHETYPE_REGISTRY.get(key, NEUTRAL_TRAITS)


def ensure_profile_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """补全孪生构建所需列，避免手写/裁剪 JSON 缺列导致 KeyError → HTTP 500。"""
    if df.empty:
        return df
    out = df.copy()
    for col, default in _PROFILE_DEFAULTS.items():
        if col not in out.columns:
            out[col] = default
    return out


@dataclass
class InterestModel:
    """兴趣偏好：主题分布、可选向量簇标签。"""

    topic_weights: dict[str, float]
    cluster_histogram: dict[int, float] = field(default_factory=dict)
    top_topics: list[str] = field(default_factory=list)


@dataclass
class BehaviorModel:
    """行为习惯：互动率、时长等统计量。"""

    like_rate: float
    comment_rate: float
    share_rate: float
    avg_duration: float
    weight_like: float
    weight_comment: float


@dataclass
class CognitiveModel:
    """认知反馈：立场分布、平均情感分。"""

    stance_weights: dict[str, float]
    mean_emotion: float
    polarization_hint: float


@dataclass
class DigitalTwinProfile:
    interest: InterestModel
    behavior: BehaviorModel
    cognitive: CognitiveModel
    memories: list[MemoryItem] = field(default_factory=list)
    agent_traits: AgentBehaviorTraits = field(default_factory=lambda: NEUTRAL_TRAITS)

    def to_json_safe_dict(self) -> dict[str, Any]:
        """可序列化快照（不含大向量时可剥离）。"""

        def mem_to_d(m: MemoryItem) -> dict[str, Any]:
            d = {
                "content_id": m.content_id,
                "text_summary": m.text_summary[:500],
                "topic": m.topic,
                "stance": m.stance,
                "timestamp": m.timestamp.isoformat(),
                "interaction_weight": m.interaction_weight,
                "raw_meta": m.raw_meta,
            }
            return d

        return {
            "interest": asdict(self.interest),
            "behavior": asdict(self.behavior),
            "cognitive": asdict(self.cognitive),
            "memory_count": len(self.memories),
            "memory_preview": [mem_to_d(m) for m in self.memories[:20]],
            "agent_traits": asdict(self.agent_traits),
        }


def build_digital_twin_profile(df: pd.DataFrame) -> DigitalTwinProfile:
    """从清洗后的用户行为表构建 1:1 孪生体三大模型与记忆流。"""
    df = ensure_profile_dataframe(df)
    if df.empty:
        return DigitalTwinProfile(
            interest=InterestModel(topic_weights={}, top_topics=[]),
            behavior=BehaviorModel(0, 0, 0, 0, 0.5, 1.0),
            cognitive=CognitiveModel({}, 3.0, 0.5),
            memories=[],
            agent_traits=resolve_agent_traits(df),
        )

    n = len(df)
    topics = df["topic"].astype(str).tolist()
    weights = np.array([behavior_weight_row(df.iloc[i]) for i in range(n)], dtype=np.float64)
    tw: dict[str, float] = {}
    for t, w in zip(topics, weights):
        tw[t] = tw.get(t, 0.0) + float(w)
    s = weights.sum() or 1.0
    tw = {k: v / s for k, v in tw.items()}
    top_topics = sorted(tw.keys(), key=lambda x: -tw[x])[:5]

    cluster_hist: dict[int, float] = {}
    if "embedding" in df.columns:
        mats = []
        for i in range(n):
            v = df.iloc[i].get("embedding")
            if v is None:
                mats = []
                break
            mats.append(np.asarray(v, dtype=np.float64).ravel())
        if len(mats) == n and n >= 2:
            X = np.stack(mats, axis=0)
            k = min(8, max(2, n // 2))
            labels = kmeans_labels(X, k=k)
            for lab, w in zip(labels, weights):
                cluster_hist[int(lab)] = cluster_hist.get(int(lab), 0.0) + float(w)
            cs = sum(cluster_hist.values()) or 1.0
            cluster_hist = {kk: vv / cs for kk, vv in cluster_hist.items()}

    likes = pd.to_numeric(df["like"], errors="coerce").fillna(0)
    comments = pd.to_numeric(df["comment"], errors="coerce").fillna(0)
    shares = pd.to_numeric(df["share"], errors="coerce").fillna(0)
    durs = pd.to_numeric(df["duration"], errors="coerce").fillna(0)
    behavior = BehaviorModel(
        like_rate=float((likes > 0).mean()),
        comment_rate=float((comments > 0).mean()),
        share_rate=float((shares > 0).mean()),
        avg_duration=float(durs.mean()),
        weight_like=float(likes.mean() or 0) + 0.5,
        weight_comment=float(comments.mean() or 0) + 1.0,
    )

    stances = df["stance"].astype(str).tolist()
    sw: dict[str, float] = {}
    for st, w in zip(stances, weights):
        sw[st] = sw.get(st, 0.0) + float(w)
    sw = {k: v / s for k, v in sw.items()}
    emo = pd.to_numeric(df["emotion_score"], errors="coerce").fillna(3.0)
    mean_em = float(emo.mean())
    dom = max(sw.values()) if sw else 1.0
    polar_hint = float(dom)

    cognitive = CognitiveModel(
        stance_weights=sw,
        mean_emotion=mean_em,
        polarization_hint=polar_hint,
    )

    memories = build_memory_stream(df)
    traits = resolve_agent_traits(df)
    return DigitalTwinProfile(
        interest=InterestModel(
            topic_weights=tw,
            cluster_histogram=cluster_hist,
            top_topics=top_topics,
        ),
        behavior=behavior,
        cognitive=cognitive,
        memories=memories,
        agent_traits=traits,
    )


def sample_twin_context_memories(profile: DigitalTwinProfile, k: int = 8) -> list[MemoryItem]:
    """为动作生成检索分层记忆子集。"""
    return stratified_memory_sample(profile.memories, k=k)
