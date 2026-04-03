from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from src.evaluation.metrics_v2 import behavior_weight_row


@dataclass
class MemoryItem:
    """孪生体记忆流单项：自然语言摘要、可选语义向量、交互权重与时间戳。"""

    content_id: str
    text_summary: str
    topic: str
    stance: str
    timestamp: datetime
    interaction_weight: float
    semantic_vector: np.ndarray | None = None
    raw_meta: dict[str, Any] = field(default_factory=dict)


def build_memory_stream(df: pd.DataFrame, semantic_summaries: list[str] | None = None) -> list[MemoryItem]:
    """由标准化行为表构建记忆流 M。"""
    items: list[MemoryItem] = []
    for pos, (i, row) in enumerate(df.iterrows()):
        ts = pd.to_datetime(row.get("timestamp"), errors="coerce")
        if pd.isna(ts):
            ts = pd.Timestamp.utcnow() + pd.Timedelta(microseconds=pos)
        summ = ""
        if semantic_summaries is not None and pos < len(semantic_summaries):
            summ = str(semantic_summaries[pos] or "")
        elif "semantic_summary" in df.columns:
            summ = str(row.get("semantic_summary", "") or "")
        else:
            summ = str(row.get("text", ""))[:200]
        w = behavior_weight_row(row)
        emb = None
        if "embedding" in df.columns:
            v = row.get("embedding")
            if v is not None:
                emb = np.asarray(v, dtype=np.float64).ravel()
        items.append(
            MemoryItem(
                content_id=str(row.get("content_id", i)),
                text_summary=summ,
                topic=str(row.get("topic", "other")),
                stance=str(row.get("stance", "neutral")),
                timestamp=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else datetime.utcnow(),
                interaction_weight=float(w),
                semantic_vector=emb,
                raw_meta={"emotion_score": float(row.get("emotion_score", 3) or 3)},
            )
        )
    return items


def memory_decay_priority(item: MemoryItem, now: datetime, decay_lambda: float = 0.05) -> float:
    """带时间衰减的检索优先级：ω * exp(-λ Δt)（Δt 为天）。"""
    delta = (now - item.timestamp).total_seconds() / 86400.0
    delta = max(delta, 0.0)
    return float(item.interaction_weight) * float(np.exp(-decay_lambda * delta))


def stratified_memory_sample(
    memories: list[MemoryItem],
    k: int,
    rng: np.random.Generator | None = None,
) -> list[MemoryItem]:
    """分层采样：高频核心 60%、低频潜在 30%、盲区负样本 10%（按主题频次分桶）。"""
    if not memories:
        return []
    rng = rng or np.random.default_rng()
    topic_w = {}
    for m in memories:
        topic_w[m.topic] = topic_w.get(m.topic, 0.0) + m.interaction_weight
    sorted_topics = sorted(topic_w.items(), key=lambda x: -x[1])
    n_top = max(1, len(sorted_topics) // 3)
    high = {t for t, _ in sorted_topics[:n_top]}
    low = {t for t, _ in sorted_topics[n_top:]}

    def bucket(m: MemoryItem) -> str:
        if m.topic in high:
            return "high"
        if m.topic in low:
            return "low"
        return "blind"

    highs = [m for m in memories if bucket(m) == "high"]
    lows = [m for m in memories if bucket(m) == "low"]
    blinds = [m for m in memories if bucket(m) == "blind"]
    if not lows and highs:
        lows = highs[-max(1, len(highs) // 4) :]
    if not blinds:
        blinds = [m for m in memories if m.topic == min(topic_w, key=lambda t: topic_w[t])][:1] or memories[:1]

    n_h = max(1, int(round(0.6 * k)))
    n_l = max(1, int(round(0.3 * k)))
    n_b = max(0, k - n_h - n_l)

    def take(pool: list[MemoryItem], n: int) -> list[MemoryItem]:
        if not pool or n <= 0:
            return []
        idx = rng.choice(len(pool), size=min(n, len(pool)), replace=False)
        return [pool[int(i)] for i in idx]

    out = take(highs, n_h) + take(lows, n_l) + take(blinds, n_b)
    if len(out) < k:
        rest = [m for m in memories if m not in out]
        need = k - len(out)
        if rest:
            idx = rng.choice(len(rest), size=min(need, len(rest)), replace=False)
            out.extend([rest[int(i)] for i in idx])
    return out[:k]
