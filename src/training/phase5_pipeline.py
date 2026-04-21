from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.training.evaluate import compare_reports
from src.training.lora_train import run_lora_training
from src.training.predict import generate_predictions


def run_phase5_pipeline(
    *,
    source: str,
    workdir: str,
    baseline_model: str,
    lora_model: str,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42,
    skip_train: bool = False,
) -> dict:
    root = Path(workdir)
    root.mkdir(parents=True, exist_ok=True)

    train_report = run_lora_training(
        source=source,
        model=baseline_model,
        workdir=str(root),
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        seed=seed,
        skip_train=skip_train,
    )
    split = train_report["split"]
    test_path = split["test_path"]

    baseline_pred = root / "predictions_baseline.json"
    lora_pred = root / "predictions_lora.json"
    baseline_pred_report = generate_predictions(
        test_path=test_path,
        output_path=str(baseline_pred),
        model=baseline_model,
        temperature=0.0,
    )
    lora_pred_report = generate_predictions(
        test_path=test_path,
        output_path=str(lora_pred),
        model=lora_model,
        temperature=0.0,
    )

    compare_report = compare_reports(test_path, str(baseline_pred), str(lora_pred))
    compare_path = root / "lora_compare.json"
    compare_path.write_text(json.dumps(compare_report, ensure_ascii=False, indent=2), encoding="utf-8")

    final_report = {
        "train_report_path": str(root / "train_report.json"),
        "train_report": train_report,
        "prediction_reports": {
            "baseline": baseline_pred_report,
            "lora": lora_pred_report,
        },
        "compare_report_path": str(compare_path),
        "compare_report": compare_report,
    }
    final_path = root / "phase5_report.json"
    final_path.write_text(json.dumps(final_report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"phase5_report_path": str(final_path), "compare_report_path": str(compare_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase5 LoRA closed-loop pipeline")
    parser.add_argument("--source", required=True, help="Annotated dataset JSON path")
    parser.add_argument("--workdir", default="outputs/phase5", help="Working directory")
    parser.add_argument("--baseline-model", required=True, help="Baseline model id/path")
    parser.add_argument("--lora-model", required=True, help="LoRA adapter model id/path")
    parser.add_argument("--train-ratio", type=float, default=0.8, help="Train split ratio")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation split ratio")
    parser.add_argument("--seed", type=int, default=42, help="Split random seed")
    parser.add_argument("--skip-train", action="store_true", help="Skip LoRA training stage")
    args = parser.parse_args()
    result = run_phase5_pipeline(
        source=args.source,
        workdir=args.workdir,
        baseline_model=args.baseline_model,
        lora_model=args.lora_model,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
        skip_train=args.skip_train,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
