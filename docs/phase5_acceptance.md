# Phase 5 Acceptance Evidence

## Scope

- Phase: `phase5-lora-training`
- Goal: deliver reproducible LoRA dataset/training/evaluation pipeline with settings-based inference switch and rollback path.

## Implemented Outcomes

- Added reproducible dataset split pipeline in `src/training/dataset.py` with `seed`, `shuffle`, ratio validation, and `split_manifest.json`.
- Enhanced training entry script `src/training/lora_train.py`:
  - supports `--train-ratio`, `--val-ratio`, `--seed`, and `--skip-train`.
  - writes `train_report.json` including reproducibility parameters and split stats.
- Added prediction script `src/training/predict.py`:
  - generates structured predictions from test split using specified model id/path.
  - output format aligned with evaluator input (`[{output: "...json..."}]`).
- Upgraded evaluation in `src/training/evaluate.py`:
  - supports single-model evaluation and baseline-vs-LoRA comparison.
  - reports `accuracy`, `topic_accuracy`, and `json_valid_rate` with deltas.
- Added LoRA inference switch controls in `src/config/settings.py` and `src/llm/providers/local_provider.py`:
  - `LORA_ENABLED`, `LORA_BASE_MODEL`, `LORA_ADAPTER_PATH`.
  - active local chat model can switch between base model and adapter path.
- Added one-command closed-loop runner `src/training/phase5_pipeline.py`:
  - steps: split dataset -> train (optional) -> baseline prediction -> LoRA prediction -> compare metrics -> final report.
  - outputs `phase5_report.json` and `lora_compare.json`.
- Added browser-triggerable API endpoint `POST /api/workbench/phase5/run` in `src/api/routers/workbench.py`:
  - supports `source_rows` direct payload mode (no manual file creation required).
  - returns report paths and active model settings for UI rendering.
- Added front-end invocation panel in `frontend/src/views/WorkbenchView.vue`:
  - can call `/api/llm/health` and `/api/workbench/phase5/run`.
  - shows JSON responses directly for in-browser verification.

## Rollback Path

- Set `LORA_ENABLED=false` to revert inference to `LOCAL_MULTIMODAL_MODEL`.
- Keep `LORA_ADAPTER_PATH` unchanged for quick re-enable without retraining.

## Verification

- Command:
  - `venv310\Scripts\python.exe -m pytest tests/test_phase5_lora_pipeline.py tests/test_phase5_closed_loop.py tests/test_workbench_phase5_api.py tests/test_llm_gateway.py -q`
- Result:
  - Phase 5 related tests pass, including split reproducibility, metric comparison, and LoRA settings validation.

## Repro Commands (venv310)

- Full closed-loop (skip train for dry-run):
  - `venv310\Scripts\python.exe -m src.training.phase5_pipeline --source data/your_annotated.json --workdir outputs/phase5 --baseline-model Qwen/Qwen2.5-7B-Instruct --lora-model outputs/phase5/adapter --skip-train`
- Train only:
  - `venv310\Scripts\python.exe -m src.training.lora_train --source data/your_annotated.json --workdir outputs/lora_run --model Qwen/Qwen2.5-7B-Instruct`
- Predict only:
  - `venv310\Scripts\python.exe -m src.training.predict --test outputs/lora_run/dataset/test.json --out outputs/base_pred.json --model Qwen/Qwen2.5-7B-Instruct`
  - `venv310\Scripts\python.exe -m src.training.predict --test outputs/lora_run/dataset/test.json --out outputs/lora_pred.json --model outputs/lora_run/adapter`
- Compare only:
  - `venv310\Scripts\python.exe -m src.training.evaluate --test outputs/lora_run/dataset/test.json --baseline-pred outputs/base_pred.json --lora-pred outputs/lora_pred.json --out outputs/lora_compare.json`
