from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_ingestion.bytes_io import load_json_from_bytes, read_csv_bytes
from src.data_ingestion.douyin_parser import _map_raw_douyin_dataframe, parse_douyin_bytes
from src.data_ingestion.schema import STANDARD_COLUMNS, normalize_topic

_DOUYIN_MARKERS = frozenset({"aweme_id", "digg_count", "desc", "create_time"})


def _column_names_lower(df: pd.DataFrame) -> set[str]:
    return {str(c).lower() for c in df.columns}


def looks_like_douyin_export(df: pd.DataFrame) -> bool:
    cols = _column_names_lower(df)
    return sum(1 for m in _DOUYIN_MARKERS if m in cols) >= 2


def read_tabular_bytes(content: bytes, suffix: str) -> pd.DataFrame:
    suf = (suffix or ".json").lower().lstrip(".")
    if suf == "csv":
        return read_csv_bytes(content)
    if suf == "json":
        data = load_json_from_bytes(content)
        rows = data if isinstance(data, list) else data.get("items", [])
        if not isinstance(rows, list):
            raise ValueError("JSON 须为数组，或根对象含 items 数组")
        return pd.DataFrame(rows)
    raise ValueError("仅支持 .csv / .json")


def ensure_standard_dataframe(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        raise ValueError("文件为空或没有可解析的数据行")
    df = raw.copy()
    for col in STANDARD_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[STANDARD_COLUMNS].copy()

    for col in ("like", "comment", "share", "duration"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["emotion_score"] = pd.to_numeric(df["emotion_score"], errors="coerce").fillna(3)

    def _str_cell(v: object) -> str:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
        s = str(v).strip()
        return "" if s.lower() == "nan" else s

    df["user_id"] = df["user_id"].map(lambda x: _str_cell(x) or "anonymous_user")
    df["platform"] = df["platform"].map(lambda x: _str_cell(x) or "unknown")
    df["content_type"] = df["content_type"].map(lambda x: _str_cell(x) or "unknown")
    df["text"] = df["text"].map(_str_cell)
    df["image_url"] = df["image_url"].map(_str_cell)
    df["video_url"] = df["video_url"].map(_str_cell)
    df["author_id"] = df["author_id"].map(_str_cell)

    cid_raw = df["content_id"].map(lambda x: _str_cell(x))
    ts = df["timestamp"].map(_str_cell)
    df["content_id"] = [cid_raw.iloc[i] or f"row_{i}" for i in range(len(df))]
    df["timestamp"] = ts

    df["topic"] = df["topic"].map(lambda x: normalize_topic(_str_cell(x)))
    df["stance"] = df["stance"].fillna("neutral").astype(str).replace("", "neutral").replace("nan", "neutral")

    return df


def import_bytes(
    content: bytes,
    filename: str,
    import_format: str,
) -> tuple[pd.DataFrame, str]:
    """
    Returns (dataframe with STANDARD_COLUMNS, detected_or_forced_format_label).
    import_format: auto | douyin | standard
    """
    suffix = Path(filename or "upload.json").suffix
    fmt = import_format.strip().lower()
    if fmt not in {"auto", "douyin", "standard"}:
        raise ValueError("format 须为 auto、douyin 或 standard")

    if fmt == "douyin":
        df = parse_douyin_bytes(content, suffix)
        return df, "douyin"

    raw = read_tabular_bytes(content, suffix)
    if raw.empty:
        raise ValueError("文件为空或没有可解析的数据行")

    if fmt == "standard":
        return ensure_standard_dataframe(raw), "standard"

    if looks_like_douyin_export(raw):
        return _map_raw_douyin_dataframe(raw), "douyin"
    return ensure_standard_dataframe(raw), "standard"
