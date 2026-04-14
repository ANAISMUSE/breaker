from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.data_ingestion.schema import normalize_topic
from src.storage.mysql_store import MySqlStore
from src.twin.twin_builder import build_digital_twin_profile


@dataclass
class PersonaProfileRecord:
    profile_id: str
    user_id: str
    profile: dict
    created_at: str


class PersonaService:
    def __init__(self) -> None:
        self.mysql = MySqlStore.from_settings() if MySqlStore.enabled() else None

    def _path(self) -> Path:
        p = Path("data/persona_profiles.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text("[]", encoding="utf-8")
        return p

    def _load(self) -> list[PersonaProfileRecord]:
        rows = json.loads(self._path().read_text(encoding="utf-8"))
        out: list[PersonaProfileRecord] = []
        for r in rows:
            out.append(
                PersonaProfileRecord(
                    profile_id=str(r.get("profile_id", "")),
                    user_id=str(r.get("user_id", "unknown")),
                    profile=r.get("profile", {}) if isinstance(r.get("profile", {}), dict) else {},
                    created_at=str(r.get("created_at", datetime.utcnow().isoformat() + "Z")),
                )
            )
        return out

    def _save(self, rows: list[PersonaProfileRecord]) -> None:
        self._path().write_text(json.dumps([asdict(r) for r in rows], ensure_ascii=False, indent=2), encoding="utf-8")

    def build_persona(self, rows: list[dict]) -> dict:
        df = pd.DataFrame(rows)
        if "topic" in df.columns:
            df["topic"] = df["topic"].astype(str).map(normalize_topic)
        profile = build_digital_twin_profile(df)
        return profile.to_json_safe_dict()

    def create_profile(self, user_id: str, profile: dict, profile_id: str | None = None) -> PersonaProfileRecord:
        record = PersonaProfileRecord(
            profile_id=profile_id or str(uuid.uuid4()),
            user_id=user_id or "unknown",
            profile=profile if isinstance(profile, dict) else {},
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        if self.mysql:
            self.mysql.create_persona_profile(record.profile_id, record.user_id, record.profile)
            return record
        rows = self._load()
        rows.append(record)
        self._save(rows)
        return record

    def create_profile_from_rows(self, rows: list[dict]) -> PersonaProfileRecord:
        profile = self.build_persona(rows)
        user_id = "unknown"
        if rows and isinstance(rows[0], dict):
            raw_uid = rows[0].get("user_id")
            if raw_uid is not None:
                user_id = str(raw_uid)
        return self.create_profile(user_id=user_id, profile=profile)

    def list_profiles(self, limit: int = 50) -> list[PersonaProfileRecord]:
        if self.mysql:
            rows = self.mysql.list_persona_profiles(limit=limit)
            return [PersonaProfileRecord(**r) for r in rows]
        rows = self._load()
        rows = sorted(rows, key=lambda x: x.created_at, reverse=True)
        return rows[: max(1, limit)]

    def get_profile(self, profile_id: str) -> PersonaProfileRecord | None:
        if self.mysql:
            row = self.mysql.get_persona_profile(profile_id)
            return PersonaProfileRecord(**row) if row else None
        for row in self._load():
            if row.profile_id == profile_id:
                return row
        return None

    def update_profile(
        self, profile_id: str, user_id: str | None = None, profile: dict | None = None
    ) -> PersonaProfileRecord | None:
        if self.mysql:
            ok = self.mysql.update_persona_profile(profile_id, user_id=user_id, profile=profile)
            if not ok:
                return None
            return self.get_profile(profile_id)
        rows = self._load()
        found = False
        for row in rows:
            if row.profile_id == profile_id:
                if user_id is not None:
                    row.user_id = user_id
                if profile is not None and isinstance(profile, dict):
                    row.profile = profile
                found = True
                break
        if not found:
            return None
        self._save(rows)
        return self.get_profile(profile_id)

    def delete_profile(self, profile_id: str) -> bool:
        if self.mysql:
            return self.mysql.delete_persona_profile(profile_id)
        rows = self._load()
        kept = [r for r in rows if r.profile_id != profile_id]
        if len(kept) == len(rows):
            return False
        self._save(kept)
        return True
