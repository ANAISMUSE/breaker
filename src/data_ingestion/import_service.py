from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.data_ingestion.bytes_io import load_json_from_bytes, read_csv_bytes
from src.data_ingestion.douyin_parser import _map_raw_douyin_dataframe, parse_douyin_bytes
from src.data_ingestion.schema import STANDARD_COLUMNS, normalize_topic

_DOUYIN_MARKERS = frozenset({"aweme_id", "digg_count", "desc", "create_time"})
_XIAOHONGSHU_MARKERS = frozenset({"note_id", "liked_count", "title", "note_type", "xsec_token"})
_WEIBO_MARKERS = frozenset({"mblogid", "attitudes_count", "reposts_count", "text_raw", "created_at"})


@dataclass
class ImportResult:
    dataframe: pd.DataFrame
    detected_format: str
    detected_platform: str
    invalid_row_count: int
    invalid_rows: list[dict]
    warnings: list[str]


def _column_names_lower(df: pd.DataFrame) -> set[str]:
    return {str(c).lower() for c in df.columns}


def looks_like_douyin_export(df: pd.DataFrame) -> bool:
    cols = _column_names_lower(df)
    return sum(1 for m in _DOUYIN_MARKERS if m in cols) >= 2


def looks_like_xiaohongshu_export(df: pd.DataFrame) -> bool:
    cols = _column_names_lower(df)
    return sum(1 for m in _XIAOHONGSHU_MARKERS if m in cols) >= 2


def looks_like_weibo_export(df: pd.DataFrame) -> bool:
    cols = _column_names_lower(df)
    return sum(1 for m in _WEIBO_MARKERS if m in cols) >= 2


def _series_or_default(raw_df: pd.DataFrame, *column_names: str, default: object) -> pd.Series:
    for name in column_names:
        if name in raw_df.columns:
            return raw_df[name]
    n = len(raw_df)
    if n == 0:
        return pd.Series([], dtype=object)
    return pd.Series([default] * n, index=raw_df.index, dtype=object)


def _map_raw_xiaohongshu_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    mapped = pd.DataFrame()
    mapped["user_id"] = _series_or_default(raw_df, "user_id", "uid", default="anonymous_user")
    mapped["platform"] = "xiaohongshu"
    if {"note_id", "id", "content_id"} & set(raw_df.columns):
        mapped["content_id"] = _series_or_default(raw_df, "note_id", "id", "content_id", default="")
    else:
        mapped["content_id"] = raw_df.index.astype(str)
    mapped["timestamp"] = _series_or_default(raw_df, "time", "create_time", "timestamp", default=None)
    mapped["content_type"] = _series_or_default(raw_df, "note_type", "content_type", default="post")
    mapped["text"] = _series_or_default(raw_df, "desc", "title", "text", default="")
    mapped["image_url"] = _series_or_default(raw_df, "image_url", "images", default="")
    mapped["video_url"] = _series_or_default(raw_df, "video_url", default="")
    mapped["like"] = pd.to_numeric(_series_or_default(raw_df, "liked_count", "like", default=0), errors="coerce").fillna(0)
    mapped["comment"] = pd.to_numeric(_series_or_default(raw_df, "comment_count", "comment", default=0), errors="coerce").fillna(0)
    mapped["share"] = pd.to_numeric(_series_or_default(raw_df, "share_count", "collect_count", "share", default=0), errors="coerce").fillna(0)
    mapped["duration"] = pd.to_numeric(_series_or_default(raw_df, "duration", default=0), errors="coerce").fillna(0)
    mapped["topic"] = _series_or_default(raw_df, "topic", "category", default="other").map(
        lambda x: normalize_topic(str(x) if pd.notna(x) else "")
    )
    mapped["stance"] = _series_or_default(raw_df, "stance", default="neutral").fillna("neutral").astype(str)
    mapped["emotion_score"] = pd.to_numeric(_series_or_default(raw_df, "emotion_score", default=3), errors="coerce").fillna(3)
    mapped["author_id"] = _series_or_default(raw_df, "author_id", "author_uid", default="")
    return ensure_standard_dataframe(mapped)


def _map_raw_weibo_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    mapped = pd.DataFrame()
    mapped["user_id"] = _series_or_default(raw_df, "user_id", "uid", default="anonymous_user")
    mapped["platform"] = "weibo"
    if {"mblogid", "id", "content_id"} & set(raw_df.columns):
        mapped["content_id"] = _series_or_default(raw_df, "mblogid", "id", "content_id", default="")
    else:
        mapped["content_id"] = raw_df.index.astype(str)
    mapped["timestamp"] = _series_or_default(raw_df, "created_at", "timestamp", default=None)
    mapped["content_type"] = _series_or_default(raw_df, "content_type", default="post")
    mapped["text"] = _series_or_default(raw_df, "text_raw", "text", default="")
    mapped["image_url"] = _series_or_default(raw_df, "image_url", default="")
    mapped["video_url"] = _series_or_default(raw_df, "video_url", "page_info", default="")
    mapped["like"] = pd.to_numeric(_series_or_default(raw_df, "attitudes_count", "like", default=0), errors="coerce").fillna(0)
    mapped["comment"] = pd.to_numeric(_series_or_default(raw_df, "comments_count", "comment", default=0), errors="coerce").fillna(0)
    mapped["share"] = pd.to_numeric(_series_or_default(raw_df, "reposts_count", "share", default=0), errors="coerce").fillna(0)
    mapped["duration"] = pd.to_numeric(_series_or_default(raw_df, "duration", default=0), errors="coerce").fillna(0)
    mapped["topic"] = _series_or_default(raw_df, "topic", "category", default="other").map(
        lambda x: normalize_topic(str(x) if pd.notna(x) else "")
    )
    mapped["stance"] = _series_or_default(raw_df, "stance", default="neutral").fillna("neutral").astype(str)
    mapped["emotion_score"] = pd.to_numeric(_series_or_default(raw_df, "emotion_score", default=3), errors="coerce").fillna(3)
    mapped["author_id"] = _series_or_default(raw_df, "author_id", default="")
    return ensure_standard_dataframe(mapped)


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


def _row_invalid_reason(row: pd.Series) -> str | None:
    text = str(row.get("text", "") or "").strip()
    image_url = str(row.get("image_url", "") or "").strip()
    video_url = str(row.get("video_url", "") or "").strip()
    timestamp = str(row.get("timestamp", "") or "").strip()
    if not text and not image_url and not video_url:
        return "empty_content"
    if not timestamp:
        return "missing_timestamp"
    return None


def validate_standard_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, int, list[dict], list[str]]:
    if df.empty:
        return df, 0, [], []
    invalid_rows: list[dict] = []
    keep_mask: list[bool] = []
    for idx, (_, row) in enumerate(df.iterrows()):
        reason = _row_invalid_reason(row)
        if reason is None:
            keep_mask.append(True)
            continue
        keep_mask.append(False)
        invalid_rows.append({"row_index": idx, "reason": reason, "content_id": str(row.get("content_id", ""))})

    valid_df = df[keep_mask].reset_index(drop=True)
    warnings: list[str] = []
    if invalid_rows:
        warnings.append(f"发现 {len(invalid_rows)} 行坏数据，已在导入阶段过滤")
    if valid_df.empty:
        raise ValueError("所有数据行均无效，请检查字段完整性（内容/时间）")
    return valid_df, len(invalid_rows), invalid_rows[:200], warnings


def import_bytes(
    content: bytes,
    filename: str,
    import_format: str,
) -> ImportResult:
    """
    Returns ImportResult with dataframe and import report.
    import_format: auto | douyin | xiaohongshu | weibo | standard
    """
    suffix = Path(filename or "upload.json").suffix
    fmt = import_format.strip().lower()
    if fmt not in {"auto", "douyin", "xiaohongshu", "weibo", "standard"}:
        raise ValueError("format 须为 auto、douyin、xiaohongshu、weibo 或 standard")

    warnings: list[str] = []
    invalid_count = 0
    invalid_rows: list[dict] = []

    if fmt == "douyin":
        df = parse_douyin_bytes(content, suffix)
        df, invalid_count, invalid_rows, warnings = validate_standard_dataframe(df)
        return ImportResult(df, "douyin", "douyin", invalid_count, invalid_rows, warnings)

    raw = read_tabular_bytes(content, suffix)
    if raw.empty:
        raise ValueError("文件为空或没有可解析的数据行")

    if fmt == "standard":
        std = ensure_standard_dataframe(raw)
        std, invalid_count, invalid_rows, warnings = validate_standard_dataframe(std)
        return ImportResult(std, "standard", "standard", invalid_count, invalid_rows, warnings)
    if fmt == "xiaohongshu":
        std = _map_raw_xiaohongshu_dataframe(raw)
        std, invalid_count, invalid_rows, warnings = validate_standard_dataframe(std)
        return ImportResult(std, "xiaohongshu", "xiaohongshu", invalid_count, invalid_rows, warnings)
    if fmt == "weibo":
        std = _map_raw_weibo_dataframe(raw)
        std, invalid_count, invalid_rows, warnings = validate_standard_dataframe(std)
        return ImportResult(std, "weibo", "weibo", invalid_count, invalid_rows, warnings)

    if looks_like_douyin_export(raw):
        std = _map_raw_douyin_dataframe(raw)
        std, invalid_count, invalid_rows, warnings = validate_standard_dataframe(std)
        return ImportResult(std, "douyin", "douyin", invalid_count, invalid_rows, warnings)
    if looks_like_xiaohongshu_export(raw):
        std = _map_raw_xiaohongshu_dataframe(raw)
        std, invalid_count, invalid_rows, warnings = validate_standard_dataframe(std)
        return ImportResult(std, "xiaohongshu", "xiaohongshu", invalid_count, invalid_rows, warnings)
    if looks_like_weibo_export(raw):
        std = _map_raw_weibo_dataframe(raw)
        std, invalid_count, invalid_rows, warnings = validate_standard_dataframe(std)
        return ImportResult(std, "weibo", "weibo", invalid_count, invalid_rows, warnings)
    std = ensure_standard_dataframe(raw)
    std, invalid_count, invalid_rows, warnings = validate_standard_dataframe(std)
    warnings.append("未识别到平台特征，已按标准格式导入")
    return ImportResult(std, "standard", "standard", invalid_count, invalid_rows, warnings)
