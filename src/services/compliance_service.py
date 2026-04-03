from __future__ import annotations

from src.compliance.audit import append_audit_log, wipe_local_session_data


class ComplianceService:
    def wipe(self, vector_store: bool, uploads: bool, tasks: bool) -> list[str]:
        return wipe_local_session_data(
            also_vector_store=vector_store,
            also_uploads=uploads,
            also_tasks=tasks,
        )

    def audit(self, event: str, detail: dict | None = None) -> None:
        append_audit_log(event, detail)

