from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class LocalVectorStore:
    def __init__(self, base_path: str = "data/vector_store.json") -> None:
        self.base_path = Path(base_path)
        self.base_path.parent.mkdir(parents=True, exist_ok=True)
        self.vectors: list[np.ndarray] = []
        self.metadata: list[dict] = []

    def add(self, vector: np.ndarray, meta: dict) -> None:
        self.vectors.append(vector.astype(np.float32))
        self.metadata.append(meta)

    def save(self) -> None:
        serializable = []
        for vec, meta in zip(self.vectors, self.metadata):
            serializable.append({"vector": vec.tolist(), "meta": meta})
        self.base_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> None:
        if not self.base_path.exists():
            return
        raw = json.loads(self.base_path.read_text(encoding="utf-8"))
        self.vectors = [np.array(item["vector"], dtype=np.float32) for item in raw]
        self.metadata = [item["meta"] for item in raw]

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> list[dict]:
        if not self.vectors:
            return []
        query = query_vector / (np.linalg.norm(query_vector) or 1.0)
        scores = []
        for idx, vec in enumerate(self.vectors):
            cand = vec / (np.linalg.norm(vec) or 1.0)
            sim = float(np.dot(query, cand))
            scores.append((sim, idx))
        scores.sort(reverse=True, key=lambda x: x[0])
        out = []
        for sim, idx in scores[:top_k]:
            out.append({"score": sim, "meta": self.metadata[idx]})
        return out
