from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.training.dataset import build_lora_splits


def _run_peft_training(train_file: str, val_file: str, model_name: str, output_dir: str) -> dict:
    try:
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "LoRA dependencies missing. Install: transformers datasets peft accelerate bitsandbytes(optional)"
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)

    def load_json(path: str) -> list[dict]:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    train_rows = load_json(train_file)
    val_rows = load_json(val_file)

    def format_rows(rows: list[dict]) -> list[dict]:
        out = []
        for row in rows:
            prompt = f"{row.get('instruction', '')}\n输入：{row.get('input', '')}\n输出："
            answer = str(row.get("output", ""))
            out.append({"text": prompt + answer})
        return out

    train_ds = Dataset.from_list(format_rows(train_rows))
    val_ds = Dataset.from_list(format_rows(val_rows))

    def tokenize(batch: dict) -> dict:
        encoded = tokenizer(batch["text"], truncation=True, max_length=1024)
        encoded["labels"] = encoded["input_ids"].copy()
        return encoded

    train_ds = train_ds.map(tokenize, remove_columns=["text"])
    val_ds = val_ds.map(tokenize, remove_columns=["text"])

    args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=8,
        num_train_epochs=1,
        learning_rate=2e-4,
        fp16=False,
        logging_steps=10,
        save_steps=100,
        evaluation_strategy="steps",
        eval_steps=100,
        report_to=[],
    )
    trainer = Trainer(model=model, args=args, train_dataset=train_ds, eval_dataset=val_ds)
    trainer.train()
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    metrics = trainer.evaluate()
    return {"status": "ok", "metrics": metrics}


def run_lora_training(
    *,
    source: str,
    model: str = "Qwen/Qwen2.5-7B-Instruct",
    workdir: str = "outputs/lora_run",
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42,
    skip_train: bool = False,
) -> dict:
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    split = build_lora_splits(
        source,
        output_dir=str(workdir / "dataset"),
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        seed=seed,
        shuffle=True,
    )
    report = {
        "model": model,
        "repro": {
            "source": source,
            "train_ratio": train_ratio,
            "val_ratio": val_ratio,
            "seed": seed,
            "skip_train": skip_train,
        },
        "split": split.__dict__,
    }
    if skip_train:
        report["train_result"] = {"status": "skipped", "reason": "skip-train flag enabled"}
    else:
        try:
            train_result = _run_peft_training(
                train_file=split.train_path,
                val_file=split.val_path,
                model_name=model,
                output_dir=str(workdir / "adapter"),
            )
            report["train_result"] = train_result
        except Exception as exc:
            report["train_result"] = {"status": "failed", "reason": str(exc)}
    (workdir / "train_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="LoRA training pipeline for Jianping")
    parser.add_argument("--source", required=True, help="Path to annotated JSON dataset")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct", help="Base model id/path")
    parser.add_argument("--workdir", default="outputs/lora_run", help="Working directory")
    parser.add_argument("--train-ratio", type=float, default=0.8, help="Train split ratio")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation split ratio")
    parser.add_argument("--seed", type=int, default=42, help="Dataset split seed")
    parser.add_argument("--skip-train", action="store_true", help="Only build split dataset and report")
    args = parser.parse_args()
    run_lora_training(
        source=args.source,
        model=args.model,
        workdir=args.workdir,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
        skip_train=args.skip_train,
    )
    print(str(Path(args.workdir) / "train_report.json"))


if __name__ == "__main__":
    main()

