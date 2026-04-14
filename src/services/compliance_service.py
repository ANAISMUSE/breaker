from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from src.compliance.audit import append_audit_log, list_audit_logs, wipe_local_session_data


class ComplianceService:
    def _policy_path(self) -> Path:
        p = Path("data/compliance_policy.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text(
                json.dumps({"auto_cleanup_enabled": False, "retention_hours": 24}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return p

    def get_policy(self) -> dict:
        try:
            return json.loads(self._policy_path().read_text(encoding="utf-8"))
        except Exception:
            return {"auto_cleanup_enabled": False, "retention_hours": 24}

    def set_policy(self, auto_cleanup_enabled: bool, retention_hours: int) -> dict:
        policy = {
            "auto_cleanup_enabled": bool(auto_cleanup_enabled),
            "retention_hours": max(1, int(retention_hours)),
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        self._policy_path().write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
        append_audit_log("compliance_policy_updated", policy)
        return policy

    def wipe(self, vector_store: bool, uploads: bool, tasks: bool) -> list[str]:
        return wipe_local_session_data(
            also_vector_store=vector_store,
            also_uploads=uploads,
            also_tasks=tasks,
        )

    def run_auto_cleanup(self) -> dict:
        policy = self.get_policy()
        if not policy.get("auto_cleanup_enabled"):
            return {"removed": [], "skipped": True, "reason": "auto cleanup disabled"}
        retention_hours = max(1, int(policy.get("retention_hours", 24)))
        expire_before = datetime.utcnow() - timedelta(hours=retention_hours)
        targets = [
            Path("data/vector_store.json"),
            Path("data/tasks_store.json"),
            Path("data/simulation_records.json"),
            Path("data/ladder_executions.json"),
            Path("data/mediacrawler_tmp.json"),
        ]
        removed: list[str] = []
        for p in targets:
            if not p.exists() or not p.is_file():
                continue
            mtime = datetime.utcfromtimestamp(p.stat().st_mtime)
            if mtime <= expire_before:
                p.unlink(missing_ok=True)
                removed.append(str(p))
        append_audit_log(
            "auto_cleanup_executed",
            {"retention_hours": retention_hours, "removed": removed, "expire_before": expire_before.isoformat() + "Z"},
        )
        return {"removed": removed, "skipped": False, "retention_hours": retention_hours}

    def export_evidence(self, limit: int = 200) -> str:
        out_dir = Path("outputs/compliance")
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"compliance_evidence_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        payload = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "policy": self.get_policy(),
            "audit_logs": list_audit_logs(limit=limit),
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        append_audit_log("compliance_evidence_exported", {"path": str(out), "limit": limit})
        return str(out)

    def audit(self, event: str, detail: dict | None = None) -> None:
        append_audit_log(event, detail)

