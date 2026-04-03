from __future__ import annotations

import math
from collections import Counter


def _normalize_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def content_diversity_score(topics: list[str]) -> float:
    if not topics:
        return 0.0
    cnt = Counter(topics)
    total = len(topics)
    probs = [v / total for v in cnt.values()]
    entropy = -sum(p * math.log(p + 1e-9, 2) for p in probs)
    max_entropy = math.log(len(cnt) + 1e-9, 2)
    ratio = entropy / (max_entropy + 1e-9) if max_entropy > 0 else 0
    return _normalize_score(ratio * 100)


def cross_domain_exposure_score(topics: list[str]) -> float:
    if not topics:
        return 0.0
    unique_ratio = len(set(topics)) / len(topics)
    return _normalize_score(unique_ratio * 200)


def polarization_risk_score(stances: list[str], emotion_scores: list[float]) -> float:
    if not stances:
        return 50.0
    dominant_ratio = Counter(stances).most_common(1)[0][1] / len(stances)
    emotion_avg = sum(emotion_scores) / max(len(emotion_scores), 1)
    risk = dominant_ratio * 70 + (emotion_avg / 5.0) * 30
    return _normalize_score(risk)


def cognitive_blindspot_score(user_dist: dict[str, float], benchmark_dist: dict[str, float]) -> float:
    keys = set(user_dist.keys()) | set(benchmark_dist.keys())
    l1_distance = 0.0
    for k in keys:
        l1_distance += abs(user_dist.get(k, 0.0) - benchmark_dist.get(k, 0.0))
    return _normalize_score(l1_distance * 50)
