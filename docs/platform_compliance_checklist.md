# Platform Collection Compliance Checklist

> Non-legal-advice engineering checklist for rollout gating.  
> Real crawling must stay disabled unless this checklist is completed and reviewed.

## 1) Regulatory Baseline (Mainland China)

- Personal Information Protection Law (PIPL): confirm lawful basis, purpose limitation, minimum necessary scope.
- Cybersecurity Law / Data Security Law: confirm classification, storage, and access controls for collected data.
- Internal governance: keep approval records for research scope, retention period, and deletion workflow.

## 2) Platform Terms Matrix (Fill Before Real Mode)

| Platform | Terms URL | Allowed data scope | Explicitly forbidden actions | Rate-limit policy | Review owner | Last review date |
|---|---|---|---|---|---|---|
| Douyin | TODO | TODO | TODO | TODO | TODO | TODO |
| Xiaohongshu | TODO | TODO | TODO | TODO | TODO | TODO |
| Weibo | TODO | TODO | TODO | TODO | TODO | TODO |
| Bilibili | TODO | TODO | TODO | TODO | TODO | TODO |
| Kuaishou | TODO | TODO | TODO | TODO | TODO | TODO |

## 3) Hard Technical Guardrails (Already Implemented)

- `CRAWLER_LEGAL_ACK=true` is required before real crawler mode can run.
- Real mode also requires:
  - `ENABLE_CLOUD_MONITOR=true`
  - `ENABLE_REAL_CRAWLER=true`
  - `MEDIACRAWLER_PROJECT_DIR` not empty
- `purpose` must be declared and be in `CRAWLER_ALLOWED_PURPOSES`.
- If any gate fails, API downgrades to demo mode and writes compliance context into audit logs.

## 4) Explicit Red Lines

- No CAPTCHA bypass / no anti-fingerprint evasion / no account-farm or cookie-pool rotation.
- No collection of non-public personal data.
- No use for ad targeting, individual profiling, or other unapproved purposes.

## 5) Evidence Pack Before Enabling Real Mode

- Completed terms matrix (Section 2).
- Signed internal review record (team advisor/supervisor).
- Latest compliance evidence export from `/api/compliance/evidence`.
- Test evidence:
  - `tests/test_realtime_compliance.py` passing in CI/local.
