from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.llm import get_llm_provider
from src.llm.gateway import extract_json_payload


def _normalize_prediction(raw: dict | list | None) -> dict:
    if isinstance(raw, dict):
        topic = str(raw.get("topic", "other")).strip() or "other"
        return {"topic": topic}
    return {"topic": "other"}


def _build_prompt(instruction: str, input_text: str) -> str:
    return (
        "你是主题分类助手。请只返回一个JSON对象，格式为 {\"topic\":\"...\"}，不要输出额外文本。\n"
        f"任务说明: {instruction}\n"
        f"输入文本: {input_text}"
    )


def _heuristic_topic(input_text: str) -> str:
    text = input_text.lower()
    if any(k in text for k in ["history", "historical", "历史"]):
        return "history"
    if any(k in text for k in ["finance", "economic", "财经", "金融"]):
        return "finance"
    if any(k in text for k in ["society", "social", "社会"]):
        return "society"
    if any(k in text for k in ["science", "scientific", "科学"]):
        return "science"
    if any(k in text for k in ["technology", "tech", "科技"]):
        return "technology"
    return "other"


def generate_predictions(
    test_path: str,
    output_path: str,
    *,
    model: str,
    temperature: float = 0.0,
) -> dict:
    rows = json.loads(Path(test_path).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("test_path must point to a JSON list")

    provider = get_llm_provider()
    predictions: list[dict] = []
    fallback_count = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        instruction = str(row.get("instruction", "")).strip()
        input_text = str(row.get("input", "")).strip()
        prompt = _build_prompt(instruction=instruction, input_text=input_text)
        try:
            result = provider.invoke_json(
                prompt=prompt,
                model=model,
                temperature=temperature,
                retry_on_parse_error=True,
            )
            parsed = result.parsed_json
            if parsed is None:
                parsed = extract_json_payload(result.content)
            normalized = _normalize_prediction(parsed)
            if normalized["topic"] == "other":
                normalized["topic"] = _heuristic_topic(input_text)
        except Exception:
            fallback_count += 1
            normalized = {"topic": _heuristic_topic(input_text)}
        predictions.append({"output": json.dumps(normalized, ensure_ascii=False)})

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(predictions, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "count": len(predictions),
        "fallback_count": fallback_count,
        "model": model,
        "output_path": str(out),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate model predictions for LoRA evaluation")
    parser.add_argument("--test", required=True, help="Path to test split json")
    parser.add_argument("--out", required=True, help="Output prediction json path")
    parser.add_argument("--model", required=True, help="Model id/path for inference")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    args = parser.parse_args()
    report = generate_predictions(
        test_path=args.test,
        output_path=args.out,
        model=args.model,
        temperature=args.temperature,
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
