from __future__ import annotations

import math
from collections import Counter

import numpy as np
import pandas as pd


# PDF 3.6.3 维度权重
W1_CONTENT = 0.2
W2_CROSS = 0.2
W3_STANCE = 0.35
W4_BLINDSPOT = 0.25


def behavior_weight_row(row: pd.Series) -> float:
    """深度互动权重：点赞/评论/分享高于纯浏览。"""
    like = float(row.get("like", 0) or 0)
    comment = float(row.get("comment", 0) or 0)
    share = float(row.get("share", 0) or 0)
    duration = float(row.get("duration", 0) or 0)
    w = 1.0 + min(like, 50) * 0.08 + min(comment, 30) * 0.25 + min(share, 20) * 0.15
    w += min(duration / 60.0, 5.0) * 0.05
    return max(w, 0.1)


def behavior_weights_for_df(df: pd.DataFrame) -> np.ndarray:
    return np.array([behavior_weight_row(df.iloc[i]) for i in range(len(df))], dtype=np.float64)


def _weighted_topic_probs(df: pd.DataFrame, weights: np.ndarray) -> tuple[dict[str, float], float]:
    topics = df["topic"].astype(str).tolist()
    total_w = float(weights.sum()) or 1.0
    acc: dict[str, float] = {}
    for t, w in zip(topics, weights):
        acc[t] = acc.get(t, 0.0) + float(w)
    return {k: v / total_w for k, v in acc.items()}, total_w


def score_s1_content_diversity(df: pd.DataFrame, weights: np.ndarray) -> float:
    """S1: 带行为权重的主题熵，归一化到 1–10。"""
    probs, _ = _weighted_topic_probs(df, weights)
    if not probs:
        return 1.0
    k = len(probs)
    h = -sum(p * math.log(p + 1e-12, 2) for p in probs.values())
    h_max = math.log(k, 2) if k > 1 else 1.0
    ratio = h / (h_max + 1e-12)
    return round(1.0 + 9.0 * ratio, 2)


def score_s2_cross_domain(
    df: pd.DataFrame,
    weights: np.ndarray,
    embeddings: np.ndarray | None = None,
) -> float:
    """S2: 跨领域内容权重占比 α，归一化到 1–10。无向量时用主题非头部占比近似。"""
    topics = df["topic"].astype(str).tolist()
    probs, total_w = _weighted_topic_probs(df, weights)
    if not probs or total_w <= 0:
        return 1.0
    sorted_topics = sorted(probs.items(), key=lambda x: -x[1])
    top2 = {t for t, _ in sorted_topics[: min(2, len(sorted_topics))]}
    cross_w = sum(weights[i] for i in range(len(df)) if topics[i] not in top2)
    alpha = cross_w / total_w

    if embeddings is not None and len(embeddings) == len(df) and len(embeddings) >= 3:
        labels = kmeans_labels(embeddings, k=min(8, max(3, len(embeddings) // 2)))
        dominant = Counter(labels).most_common(1)[0][0]
        cross_w2 = sum(weights[i] for i in range(len(df)) if labels[i] != dominant)
        alpha = 0.5 * alpha + 0.5 * (cross_w2 / total_w)

    alpha = min(max(alpha, 0.0), 1.0)
    return round(1.0 + 9.0 * alpha, 2)


def _gini_stance_concentration(probs: dict[str, float]) -> float:
    """0=均匀（低极化），1=单峰（高极化）。"""
    if not probs:
        return 1.0
    s = len(probs)
    p = np.array(list(probs.values()), dtype=np.float64)
    p = p / (p.sum() + 1e-12)
    h = float(np.sum(p**2))
    if s <= 1:
        return 1.0
    h_min = 1.0 / s
    g = (h - h_min) / (1.0 - h_min + 1e-12)
    return min(max(g, 0.0), 1.0)


def score_s3_stance_diversity(df: pd.DataFrame, weights: np.ndarray) -> float:
    """S3: 立场分布基尼型集中度，S3 = 1 + 9*(1-G)。"""
    stances = df["stance"].astype(str).tolist()
    total_w = float(weights.sum()) or 1.0
    acc: dict[str, float] = {}
    for st, w in zip(stances, weights):
        acc[st] = acc.get(st, 0.0) + float(w)
    probs = {k: v / total_w for k, v in acc.items()}
    g = _gini_stance_concentration(probs)
    return round(1.0 + 9.0 * (1.0 - g), 2)


def score_s4_cognitive_coverage(
    df: pd.DataFrame,
    weights: np.ndarray,
    benchmark_dist: dict[str, float],
    embeddings: np.ndarray | None = None,
) -> float:
    """S4: 与对标分布的覆盖 + 可选语义簇覆盖，归一化 1–10。"""
    probs, total_w = _weighted_topic_probs(df, weights)
    keys = set(benchmark_dist.keys()) | set(probs.keys())
    if not keys:
        return 1.0
    b_sum = sum(benchmark_dist.values()) or 1.0
    b_norm = {k: float(benchmark_dist.get(k, 0)) / b_sum for k in keys}
    u_norm = {k: float(probs.get(k, 0.0)) for k in keys}
    overlap = sum(min(u_norm[k], b_norm[k]) for k in keys)
    r_topic = min(1.0, 2.0 * overlap / (sum(b_norm.values()) + 1e-12))

    r_embed = r_topic
    if embeddings is not None and len(embeddings) == len(df) and len(embeddings) >= 3:
        k_cl = min(10, max(3, len(embeddings) // 2))
        labels = kmeans_labels(embeddings, k=k_cl)
        covered = len(set(labels))
        r_embed = covered / float(k_cl)

    r = 0.6 * r_topic + 0.4 * r_embed
    r = min(max(r, 0.0), 1.0)
    return round(1.0 + 9.0 * r, 2)


def cocoon_index_from_scores(s1: float, s2: float, s3: float, s4: float) -> float:
    """C = 10 - (w1*S1 + w2*S2 + w3*S3 + w4*S4)，0–10 越高茧房越严重。"""
    inner = W1_CONTENT * s1 + W2_CROSS * s2 + W3_STANCE * s3 + W4_BLINDSPOT * s4
    c = 10.0 - inner
    return round(min(max(c, 0.0), 10.0), 2)


def kmeans_labels(X: np.ndarray, k: int, max_iter: int = 25, seed: int = 42) -> np.ndarray:
    """轻量 K-Means，仅依赖 numpy。"""
    n, d = X.shape
    k = int(max(1, min(k, n)))
    if k == 1:
        return np.zeros(n, dtype=np.int32)
    rng = np.random.default_rng(seed)
    idx = rng.choice(n, size=k, replace=False)
    centers = X[idx].copy()
    labels = np.zeros(n, dtype=np.int32)
    for _ in range(max_iter):
        dists = np.linalg.norm(X[:, None, :] - centers[None, :, :], axis=2)
        new_labels = np.argmin(dists, axis=1).astype(np.int32)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for j in range(k):
            mask = labels == j
            if np.any(mask):
                centers[j] = X[mask].mean(axis=0)
            else:
                centers[j] = X[rng.integers(0, n)]
    return labels


def dataframe_embeddings_matrix(df: pd.DataFrame) -> np.ndarray | None:
    if "embedding" not in df.columns or df.empty:
        return None
    rows = []
    for v in df["embedding"]:
        if v is None:
            return None
        arr = np.asarray(v, dtype=np.float64).ravel()
        if arr.size == 0:
            return None
        rows.append(arr)
    if not rows:
        return None
    try:
        return np.stack(rows, axis=0)
    except ValueError:
        return None
