# Phase 6 Acceptance Evidence (In Progress)

## Scope

- Phase: `phase6-multi-platform-ingest`
- Goal: deliver multi-platform ingestion under a unified schema with auditable legal-compliance gates.

## Current Progress

- Platform mapping status:
  - `douyin` / `xiaohongshu` / `weibo` support platform-specific mapping to standard schema.
  - `bilibili` / `kuaishou` currently use standard-schema fallback mapping with platform override.
- Compliance gate status:
  - Real crawler mode is now blocked unless all conditions are met:
    - `ENABLE_CLOUD_MONITOR=true`
    - `ENABLE_REAL_CRAWLER=true`
    - `CRAWLER_LEGAL_ACK=true`
    - `MEDIACRAWLER_PROJECT_DIR` is not empty
  - Realtime API response now includes:
    - `legal_ack`
    - `compliance_gate_reason`
    - `purpose`
    - `purpose_allowed`
  - Audit log now records compliance context on crawl completion.
  - Purpose control:
    - `purpose` must be in `CRAWLER_ALLOWED_PURPOSES`.
    - if purpose is not allowed, API downgrades to demo mode even when legal ack is enabled.
- Added compliance checklist:
  - `docs/platform_compliance_checklist.md` (regulatory baseline + platform terms matrix + red lines).

## Legal/Regulatory Baseline (to be completed)

- Personal information protection:
  - Confirm data minimization for ingestion fields.
  - Confirm storage retention period and deletion workflow.
- Platform terms compliance:
  - Build platform-by-platform collection policy matrix (allowed scope, forbidden actions, rate limits).
- User rights and traceability:
  - Keep immutable audit entries for collection events and degraded fallbacks.

## Remaining Acceptance Tasks

- Expand automated test coverage from legal-ack gate to additional gate combinations and error fallback paths.
- Add platform field-coverage report and failure-degrade evidence.
- Attach final checklist proving legal ack + policy documentation is present before real-mode rollout.

## Verification (Current)

- Command:
  - `venv310\Scripts\python.exe -m pytest tests/test_realtime_compliance.py -q`
- Result:
  - `3 passed`
  - Covers:
    - `/api/realtime/status` legal gate response and allowed purpose exposure.
    - `/api/realtime/crawl-preview` downgrade + audit fields when `CRAWLER_LEGAL_ACK=false`.
    - `/api/realtime/crawl-preview` purpose gate (invalid purpose blocked and downgraded).
