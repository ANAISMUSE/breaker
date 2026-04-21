from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_json_list(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("input file must be a JSON list")
    return [x for x in data if isinstance(x, dict)]


def _extract_topic(value: str) -> tuple[str, bool]:
    raw = str(value or "").strip()
    if not raw:
        return "other", False
    try:
        obj = json.loads(raw)
    except Exception:
        return "other", False
    if not isinstance(obj, dict):
        return "other", False
    topic = str(obj.get("topic", "other")).strip() or "other"
    return topic, True


def evaluate_predictions(test_path: str, pred_path: str) -> dict:
    tests = _load_json_list(test_path)
    preds = _load_json_list(pred_path)
    if not isinstance(tests, list) or not isinstance(preds, list):
        raise ValueError("test and prediction files must be JSON lists")
    n = min(len(tests), len(preds))
    if n == 0:
        return {"count": 0, "accuracy": 0.0, "topic_accuracy": 0.0, "json_valid_rate": 0.0}
    exact_hit = 0
    topic_hit = 0
    valid_json = 0
    for i in range(n):
        gt = str(tests[i].get("output", ""))
        pd = str(preds[i].get("output", ""))
        if gt == pd:
            exact_hit += 1
        gt_topic, gt_ok = _extract_topic(gt)
        pd_topic, pd_ok = _extract_topic(pd)
        if gt_ok and pd_ok and gt_topic == pd_topic:
            topic_hit += 1
        if pd_ok:
            valid_json += 1
    return {
        "count": n,
        "accuracy": round(exact_hit / n, 4),
        "topic_accuracy": round(topic_hit / n, 4),
        "json_valid_rate": round(valid_json / n, 4),
    }


def compare_reports(test_path: str, baseline_pred_path: str, lora_pred_path: str) -> dict:
    baseline = evaluate_predictions(test_path, baseline_pred_path)
    lora = evaluate_predictions(test_path, lora_pred_path)
    return {
        "count": min(baseline["count"], lora["count"]),
        "baseline": baseline,
        "lora": lora,
        "delta": {
            "accuracy": round(lora["accuracy"] - baseline["accuracy"], 4),
            "topic_accuracy": round(lora["topic_accuracy"] - baseline["topic_accuracy"], 4),
            "json_valid_rate": round(lora["json_valid_rate"] - baseline["json_valid_rate"], 4),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate LoRA outputs")
    parser.add_argument("--test", required=True, help="Path to test split json")
    parser.add_argument("--pred", help="Path to a single prediction json")
    parser.add_argument("--baseline-pred", help="Path to baseline model predictions")
    parser.add_argument("--lora-pred", help="Path to LoRA model predictions")
    parser.add_argument("--out", default="outputs/lora_eval.json", help="Output report path")
    args = parser.parse_args()
    if args.pred:
        result = evaluate_predictions(args.test, args.pred)
    else:
        if not args.baseline_pred or not args.lora_pred:
            raise ValueError("Use --pred for single model or provide both --baseline-pred and --lora-pred.")
        result = compare_reports(args.test, args.baseline_pred, args.lora_pred)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out))


if __name__ == "__main__":
    main()

