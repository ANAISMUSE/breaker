from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LoraSplitResult:
    train_path: str
    val_path: str
    test_path: str
    train_count: int
    val_count: int
    test_count: int


def _normalize_row(row: dict) -> dict:
    text = str(row.get("text", "")).strip()
    label = str(row.get("label", row.get("topic", "other"))).strip() or "other"
    return {
        "instruction": "请识别这条社交媒体内容的主题标签并给出简述。",
        "input": text,
        "output": json.dumps({"topic": label}, ensure_ascii=False),
    }


def build_lora_splits(
    source_path: str,
    output_dir: str = "data/lora_dataset",
    *,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42,
    shuffle: bool = True,
) -> LoraSplitResult:
    if train_ratio <= 0 or val_ratio < 0:
        raise ValueError("train_ratio must be > 0 and val_ratio must be >= 0")
    if train_ratio + val_ratio >= 1.0:
        raise ValueError("train_ratio + val_ratio must be < 1.0")

    src = Path(source_path)
    data = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("source dataset must be a JSON list")
    rows = [_normalize_row(x) for x in data if isinstance(x, dict)]
    if len(rows) < 20:
        raise ValueError("dataset too small, expected at least 20 samples")

    n = len(rows)
    if shuffle:
        rng = random.Random(seed)
        rng.shuffle(rows)

    train_n = int(n * train_ratio)
    val_n = int(n * val_ratio)
    test_n = n - train_n - val_n
    if test_n <= 0:
        test_n = 1
        train_n = max(1, train_n - 1)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    train = rows[:train_n]
    val = rows[train_n : train_n + val_n]
    test = rows[train_n + val_n :]

    train_path = out_dir / "train.json"
    val_path = out_dir / "val.json"
    test_path = out_dir / "test.json"
    train_path.write_text(json.dumps(train, ensure_ascii=False, indent=2), encoding="utf-8")
    val_path.write_text(json.dumps(val, ensure_ascii=False, indent=2), encoding="utf-8")
    test_path.write_text(json.dumps(test, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "source": str(src),
        "seed": seed,
        "shuffle": shuffle,
        "split_ratio": {
            "train": train_ratio,
            "val": val_ratio,
            "test": round(1.0 - train_ratio - val_ratio, 6),
        },
        "counts": {
            "total": n,
            "train": len(train),
            "val": len(val),
            "test": len(test),
        },
        "files": {
            "train": str(train_path),
            "val": str(val_path),
            "test": str(test_path),
        },
    }
    (out_dir / "split_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return LoraSplitResult(
        train_path=str(train_path),
        val_path=str(val_path),
        test_path=str(test_path),
        train_count=len(train),
        val_count=len(val),
        test_count=len(test),
    )

