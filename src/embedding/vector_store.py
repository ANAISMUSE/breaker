from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


class LocalVectorStore:
    def __init__(self, base_path: str = "data/vector_store.json") -> None:
        self.base_path = Path(base_path)
        self.base_path.parent.mkdir(parents=True, exist_ok=True)
        self.vectors: list[np.ndarray] = []
        self.metadata: list[dict] = []
        self.vector_bundles: list[dict[str, list[float]]] = []
        self.vector_version: list[str] = []
        self.metadata_version: list[str] = []

    def add(
        self,
        vector: np.ndarray,
        meta: dict[str, Any],
        *,
        vector_bundle: dict[str, np.ndarray] | None = None,
        version: str = "v1",
        metadata_version: str = "m1",
    ) -> None:
        base_vec = vector.astype(np.float32)
        self.vectors.append(base_vec)
        self.metadata.append(meta)
        bundle = vector_bundle or {"fused": base_vec}
        serial_bundle: dict[str, list[float]] = {}
        for key, arr in bundle.items():
            serial_bundle[str(key)] = np.asarray(arr, dtype=np.float32).ravel().tolist()
        if "fused" not in serial_bundle:
            serial_bundle["fused"] = base_vec.ravel().tolist()
        self.vector_bundles.append(serial_bundle)
        self.vector_version.append(version)
        self.metadata_version.append(metadata_version)

    def save(self) -> None:
        serializable = []
        for vec, meta, bundle, version, meta_version in zip(
            self.vectors, self.metadata, self.vector_bundles, self.vector_version, self.metadata_version
        ):
            serializable.append(
                {
                    "vector": vec.tolist(),
                    "meta": meta,
                    "vector_bundle": bundle,
                    "version": version,
                    "metadata_version": meta_version,
                }
            )
        self.base_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> None:
        if not self.base_path.exists():
            return
        raw = json.loads(self.base_path.read_text(encoding="utf-8"))
        self.vectors = [np.array(item["vector"], dtype=np.float32) for item in raw]
        self.metadata = [item["meta"] for item in raw]
        self.vector_bundles = [item.get("vector_bundle", {"fused": item["vector"]}) for item in raw]
        self.vector_version = [str(item.get("version", "v1")) for item in raw]
        self.metadata_version = [str(item.get("metadata_version", "m1")) for item in raw]

    def search(self, query_vector: np.ndarray, top_k: int = 5, vector_field: str = "fused") -> list[dict]:
        if not self.vectors:
            return []
        query = query_vector / (np.linalg.norm(query_vector) or 1.0)
        scores = []
        for idx, vec in enumerate(self.vectors):
            bundle = self.vector_bundles[idx] if idx < len(self.vector_bundles) else {}
            primary = bundle.get(vector_field) or bundle.get("fused")
            if primary is None:
                primary = vec
            cand_vec = np.asarray(primary, dtype=np.float32)
            cand = cand_vec / (np.linalg.norm(cand_vec) or 1.0)
            sim = float(np.dot(query, cand))
            scores.append((sim, idx))
        scores.sort(reverse=True, key=lambda x: x[0])
        out = []
        for sim, idx in scores[:top_k]:
            out.append(
                {
                    "score": sim,
                    "meta": self.metadata[idx],
                    "vector_bundle": self.vector_bundles[idx] if idx < len(self.vector_bundles) else {},
                    "version": self.vector_version[idx] if idx < len(self.vector_version) else "v1",
                    "metadata_version": self.metadata_version[idx] if idx < len(self.metadata_version) else "m1",
                }
            )
        return out

    def hybrid_search(
        self,
        query_vectors: dict[str, np.ndarray],
        *,
        top_k: int = 5,
        field_weights: dict[str, float] | None = None,
    ) -> list[dict]:
        if not self.vectors:
            return []
        if not query_vectors:
            return []
        weights = field_weights or {name: 1.0 for name in query_vectors.keys()}
        norm_weights = {k: max(0.0, float(v)) for k, v in weights.items()}
        weight_sum = sum(norm_weights.values()) or 1.0
        normalized_q: dict[str, np.ndarray] = {}
        for name, vec in query_vectors.items():
            arr = np.asarray(vec, dtype=np.float32).ravel()
            normalized_q[name] = arr / (np.linalg.norm(arr) or 1.0)

        scores = []
        for idx, vec in enumerate(self.vectors):
            bundle = self.vector_bundles[idx] if idx < len(self.vector_bundles) else {}
            base = np.asarray(bundle.get("fused", vec), dtype=np.float32).ravel()
            total_score = 0.0
            for field_name, q in normalized_q.items():
                w = norm_weights.get(field_name, 0.0) / weight_sum
                candidate = bundle.get(field_name, bundle.get("fused"))
                cand = np.asarray(candidate if candidate is not None else base, dtype=np.float32).ravel()
                cand = cand / (np.linalg.norm(cand) or 1.0)
                total_score += w * float(np.dot(q, cand))
            scores.append((total_score, idx))
        scores.sort(reverse=True, key=lambda x: x[0])
        out = []
        for sim, idx in scores[:top_k]:
            out.append(
                {
                    "score": sim,
                    "meta": self.metadata[idx],
                    "vector_bundle": self.vector_bundles[idx] if idx < len(self.vector_bundles) else {},
                    "version": self.vector_version[idx] if idx < len(self.vector_version) else "v1",
                    "metadata_version": self.metadata_version[idx] if idx < len(self.metadata_version) else "m1",
                }
            )
        return out
