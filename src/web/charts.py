from __future__ import annotations

from src.evaluation.index_pipeline import EvaluationResult, EvaluationResultV2


def radar_option(result: EvaluationResult) -> dict:
    return {
        "tooltip": {},
        "radar": {
            "indicator": [
                {"name": "内容多样性", "max": 100},
                {"name": "跨域曝光", "max": 100},
                {"name": "极化风险", "max": 100},
                {"name": "认知盲区", "max": 100},
            ]
        },
        "series": [
            {
                "type": "radar",
                "data": [
                    {
                        "value": [
                            result.content_diversity,
                            result.cross_domain_exposure,
                            result.polarization_risk,
                            result.cognitive_blindspot,
                        ],
                        "name": "茧房四维评分",
                    }
                ],
            }
        ],
    }


def radar_option_v2(ev: EvaluationResultV2) -> dict:
    """PDF 3.6：S1–S4 为 1–10，越高表示多样性越好。"""
    return {
        "tooltip": {},
        "radar": {
            "indicator": [
                {"name": "S1 内容多样性", "max": 10},
                {"name": "S2 跨域曝光", "max": 10},
                {"name": "S3 立场多样性", "max": 10},
                {"name": "S4 认知覆盖", "max": 10},
            ]
        },
        "series": [
            {
                "type": "radar",
                "data": [
                    {
                        "value": [
                            ev.s1_content_diversity,
                            ev.s2_cross_domain,
                            ev.s3_stance_diversity,
                            ev.s4_cognitive_coverage,
                        ],
                        "name": "多样性得分",
                    }
                ],
            }
        ],
    }


def cocoon_trend_option(series_by_strategy: dict[str, list[float]]) -> dict:
    """多策略茧房指数（0–10）折线对比。"""
    names = [k for k in series_by_strategy if not k.startswith("_")]
    if not names:
        return {}
    max_len = max(len(series_by_strategy[k]) for k in names)
    x_axis = [f"R{i+1}" for i in range(max_len)]
    ser = []
    for name in names:
        y = series_by_strategy[name]
        padded = y + [y[-1]] * (max_len - len(y)) if y else [0] * max_len
        ser.append({"name": name, "type": "line", "data": padded[:max_len]})
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"data": names},
        "xAxis": {"type": "category", "data": x_axis},
        "yAxis": {"type": "value", "min": 0, "max": 10, "name": "茧房指数"},
        "series": ser,
    }


def topic_pie_option(topic_counts: dict[str, int]) -> dict:
    data = [{"name": k, "value": v} for k, v in topic_counts.items()]
    return {"tooltip": {"trigger": "item"}, "series": [{"type": "pie", "radius": "65%", "data": data}]}
