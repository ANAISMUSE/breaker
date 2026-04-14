from __future__ import annotations

from math import log2
import json
from pathlib import Path
import pandas as pd

from src.evaluation.index_pipeline import EvaluationResultV2, evaluate_cocoon_pdf36
from src.evaluation.metrics_v2 import behavior_weight_row, dataframe_embeddings_matrix


class RiskService:
    def evaluate_overview(self, df: pd.DataFrame, benchmark: dict[str, float]) -> EvaluationResultV2:
        return evaluate_cocoon_pdf36(df, benchmark, mode="static")

    def evaluate_detail(self, df: pd.DataFrame, benchmark: dict[str, float]) -> dict:
        ev = self.evaluate_overview(df, benchmark)
        topic_dist = self._weighted_dist(df, "topic")
        stance_dist = self._weighted_dist(df, "stance")
        benchmark_dist = self._normalize_dist(benchmark)
        alignment = self._l1_alignment(topic_dist, benchmark_dist)

        s1_info = self._s1_entropy(topic_dist)
        s2_info = self._s2_cross(topic_dist)
        s3_info = self._s3_gini(stance_dist)
        s4_info = self._s4_overlap(topic_dist, benchmark_dist)

        cohort = self._cohort_comparison(df, benchmark, ev)
        trend = self._trend_30d(df, benchmark)

        return {
            "overview": ev.__dict__,
            "llm": self._llm_info(df),
            "cohort": cohort,
            "trend_30d": trend,
            "distributions": {
                "topic": topic_dist,
                "stance": stance_dist,
                "benchmark": benchmark_dist,
                "alignment": alignment,
            },
            "derived": {
                "s1_entropy": s1_info,
                "s2_cross": s2_info,
                "s3_gini": s3_info,
                "s4_overlap": s4_info,
            },
            "suggestions": {
                "s2": self._build_s2_suggestion(ev.s2_cross_domain, s2_info, topic_dist, benchmark_dist),
                "s4": self._build_s4_suggestion(ev.s4_cognitive_coverage, s4_info, topic_dist, benchmark_dist),
            },
        }

    def _load_group_benchmarks(self) -> dict[str, dict[str, float]]:
        path = Path("data/group_benchmarks.json")
        if not path.exists():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(raw, dict):
            return {}
        out: dict[str, dict[str, float]] = {}
        for k, v in raw.items():
            if isinstance(v, dict):
                out[str(k)] = {str(kk): float(vv) for kk, vv in v.items() if isinstance(vv, (int, float))}
        return out

    def _resolve_group_key(self, df: pd.DataFrame) -> str:
        if not df.empty and "age_group" in df.columns:
            v = str(df["age_group"].iloc[0] or "").strip()
            if v:
                return f"age:{v}"
        if not df.empty and "persona_preset" in df.columns:
            v = str(df["persona_preset"].iloc[0] or "").strip()
            if v:
                return f"persona:{v}"
        if not df.empty and "platform" in df.columns:
            v = str(df["platform"].iloc[0] or "").strip()
            if v:
                return f"platform:{v}"
        return "global"

    def _cohort_comparison(self, df: pd.DataFrame, benchmark: dict[str, float], ev: EvaluationResultV2) -> dict:
        group_key = self._resolve_group_key(df)
        catalog = self._load_group_benchmarks()
        cohort_benchmark = catalog.get(group_key) or catalog.get("global") or benchmark
        cohort_ev = evaluate_cocoon_pdf36(df, cohort_benchmark, mode="static")
        return {
            "group_key": group_key,
            "benchmark_topics": len(cohort_benchmark),
            "cohort_overview": cohort_ev.__dict__,
            "delta_vs_cohort": {
                "s1": round(ev.s1_content_diversity - cohort_ev.s1_content_diversity, 3),
                "s2": round(ev.s2_cross_domain - cohort_ev.s2_cross_domain, 3),
                "s3": round(ev.s3_stance_diversity - cohort_ev.s3_stance_diversity, 3),
                "s4": round(ev.s4_cognitive_coverage - cohort_ev.s4_cognitive_coverage, 3),
                "c": round(ev.cocoon_index - cohort_ev.cocoon_index, 3),
            },
        }

    def _trend_30d(self, df: pd.DataFrame, benchmark: dict[str, float]) -> dict:
        if df.empty or "timestamp" not in df.columns:
            return {"points": [], "window_days": 30}
        work = df.copy()
        work["timestamp"] = pd.to_datetime(work["timestamp"], errors="coerce")
        work = work.dropna(subset=["timestamp"]).sort_values("timestamp")
        if work.empty:
            return {"points": [], "window_days": 30}
        end_day = work["timestamp"].max().normalize()
        start_day = end_day - pd.Timedelta(days=29)
        trend_points: list[dict] = []
        for d in pd.date_range(start_day, end_day, freq="D"):
            cut = work[work["timestamp"] <= (d + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))]
            if cut.empty:
                continue
            ev = evaluate_cocoon_pdf36(cut, benchmark, mode="static")
            trend_points.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "row_count": int(len(cut)),
                    "cocoon_index": ev.cocoon_index,
                    "s1": ev.s1_content_diversity,
                    "s2": ev.s2_cross_domain,
                    "s3": ev.s3_stance_diversity,
                    "s4": ev.s4_cognitive_coverage,
                }
            )
        return {"points": trend_points, "window_days": 30}

    def _llm_info(self, df: pd.DataFrame) -> dict:
        emb = dataframe_embeddings_matrix(df)
        semantic_rows = 0
        for _, row in df.iterrows():
            if str(row.get("semantic_summary", "")).strip():
                semantic_rows += 1
        evidence = []
        if "semantic_summary" in df.columns:
            for _, row in df.head(5).iterrows():
                summary = str(row.get("semantic_summary", "")).strip()
                if summary:
                    evidence.append(
                        {
                            "content_id": str(row.get("content_id", "")),
                            "topic": str(row.get("topic", "other")),
                            "summary": summary[:160],
                        }
                    )
        return {
            "llm_enhanced": emb is not None,
            "embedding_rows": int(len(df)) if emb is not None else 0,
            "semantic_rows": semantic_rows,
            "evidence": evidence,
        }

    def _weighted_dist(self, df: pd.DataFrame, col: str) -> dict[str, float]:
        if df.empty or col not in df.columns:
            return {}
        out: dict[str, float] = {}
        total = 0.0
        for _, row in df.iterrows():
            key = str(row.get(col, "")).strip()
            if not key:
                continue
            w = float(behavior_weight_row(row))
            out[key] = out.get(key, 0.0) + w
            total += w
        if total <= 0:
            return {}
        return {k: v / total for k, v in out.items()}

    def _normalize_dist(self, raw: dict[str, float]) -> dict[str, float]:
        out: dict[str, float] = {}
        total = 0.0
        for k, v in raw.items():
            value = max(0.0, float(v))
            out[k] = value
            total += value
        if total <= 0:
            return {}
        return {k: v / total for k, v in out.items()}

    def _l1_alignment(self, a: dict[str, float], b: dict[str, float]) -> float:
        keys = set(a.keys()) | set(b.keys())
        l1 = 0.0
        for k in keys:
            l1 += abs(a.get(k, 0.0) - b.get(k, 0.0))
        return max(0.0, min(1.0, 1.0 - l1 / 2.0))

    def _s1_entropy(self, topic_dist: dict[str, float]) -> dict:
        k = len(topic_dist)
        if k <= 1:
            return {"h": 0.0, "h_max": 1.0, "ratio": 0.0}
        h = 0.0
        for p in topic_dist.values():
            if p > 0:
                h += -(p * log2(p))
        h_max = log2(k)
        ratio = h / h_max if h_max > 0 else 0.0
        return {"h": h, "h_max": h_max, "ratio": max(0.0, min(1.0, ratio))}

    def _s2_cross(self, topic_dist: dict[str, float]) -> dict:
        sorted_topics = sorted(topic_dist.items(), key=lambda x: x[1], reverse=True)
        top2 = [x[0] for x in sorted_topics[:2]]
        top2_prob = sum(topic_dist.get(x, 0.0) for x in top2)
        alpha = max(0.0, min(1.0, 1.0 - top2_prob))
        return {"top2": top2, "top2_prob": top2_prob, "alpha": alpha}

    def _s3_gini(self, stance_dist: dict[str, float]) -> dict:
        s = len(stance_dist)
        if s <= 1:
            return {"count": s, "gini": 1.0}
        sum_sq = sum(p * p for p in stance_dist.values())
        h_min = 1.0 / s
        gini = (sum_sq - h_min) / (1.0 - h_min + 1e-12)
        return {"count": s, "gini": max(0.0, min(1.0, gini))}

    def _s4_overlap(self, topic_dist: dict[str, float], benchmark_dist: dict[str, float]) -> dict:
        keys = set(topic_dist.keys()) | set(benchmark_dist.keys())
        overlap = 0.0
        for k in keys:
            overlap += min(topic_dist.get(k, 0.0), benchmark_dist.get(k, 0.0))
        return {"overlap": overlap, "r_topic": min(1.0, overlap * 2.0)}

    def _severity(self, score: float) -> str:
        if score < 4:
            return "high"
        if score < 7:
            return "medium"
        return "low"

    def _build_s2_suggestion(
        self, s2_score: float, s2_info: dict, topic_dist: dict[str, float], benchmark_dist: dict[str, float]
    ) -> dict | None:
        severity = self._severity(s2_score)
        if severity == "low":
            return None
        target_s2 = 8.0 if severity == "high" else 7.0
        alpha_now = float(s2_info.get("alpha", 0.0))
        alpha_target = max(0.0, min(1.0, (target_s2 - 1.0) / 9.0))
        top2 = set(s2_info.get("top2", []))
        gaps = []
        for topic, b in benchmark_dist.items():
            if topic in top2:
                continue
            u = topic_dist.get(topic, 0.0)
            deficit = max(0.0, b - u)
            if deficit > 0:
                gaps.append({"topic": topic, "benchmark": b, "actual": u, "deficit": deficit})
        gaps.sort(key=lambda x: x["deficit"], reverse=True)
        return {
            "severity": severity,
            "target_s2": target_s2,
            "alpha_now": alpha_now,
            "alpha_target": alpha_target,
            "top2_topics": list(top2),
            "recommended_topics": gaps[:6],
        }

    def _build_s4_suggestion(
        self, s4_score: float, s4_info: dict, topic_dist: dict[str, float], benchmark_dist: dict[str, float]
    ) -> dict | None:
        severity = self._severity(s4_score)
        if severity == "low":
            return None
        target_s4 = 8.0 if severity == "high" else 7.0
        overlap_now = float(s4_info.get("overlap", 0.0))
        overlap_target = max(0.0, min(0.5, ((target_s4 - 1.0) / 9.0) / 2.0))
        keys = set(topic_dist.keys()) | set(benchmark_dist.keys())
        gaps = []
        for topic in keys:
            b = benchmark_dist.get(topic, 0.0)
            u = topic_dist.get(topic, 0.0)
            deficit = max(0.0, b - u)
            if deficit > 0:
                gaps.append({"topic": topic, "benchmark": b, "actual": u, "deficit": deficit})
        gaps.sort(key=lambda x: x["deficit"], reverse=True)
        return {
            "severity": severity,
            "target_s4": target_s4,
            "overlap_now": overlap_now,
            "overlap_target": overlap_target,
            "recommended_topics": gaps[:6],
        }

