from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.data_ingestion.bytes_io import load_json_from_bytes, read_csv_bytes
from src.data_ingestion.schema import STANDARD_COLUMNS, normalize_topic


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in STANDARD_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[STANDARD_COLUMNS]


def _series_or_default(raw_df: pd.DataFrame, *column_names: str, default: object) -> pd.Series:
    for name in column_names:
        if name in raw_df.columns:
            return raw_df[name]
    n = len(raw_df)
    if n == 0:
        return pd.Series([], dtype=object)
    return pd.Series([default] * n, index=raw_df.index, dtype=object)


def _map_raw_douyin_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    mapped = pd.DataFrame()
    mapped["user_id"] = _series_or_default(raw_df, "user_id", default="anonymous_user")
    mapped["platform"] = "douyin"
    if "aweme_id" in raw_df.columns:
        mapped["content_id"] = raw_df["aweme_id"]
    elif "content_id" in raw_df.columns:
        mapped["content_id"] = raw_df["content_id"]
    else:
        mapped["content_id"] = raw_df.index.astype(str)
    ts = _series_or_default(raw_df, "create_time", "timestamp", default=None)
    mapped["timestamp"] = ts
    mapped["content_type"] = _series_or_default(raw_df, "content_type", default="video")
    mapped["text"] = _series_or_default(raw_df, "desc", "text", default="")
    mapped["image_url"] = _series_or_default(raw_df, "image_url", default="")
    mapped["video_url"] = _series_or_default(raw_df, "video_url", default="")
    mapped["like"] = pd.to_numeric(_series_or_default(raw_df, "digg_count", "like", default=0), errors="coerce").fillna(0)
    mapped["comment"] = pd.to_numeric(
        _series_or_default(raw_df, "comment_count", "comment", default=0), errors="coerce"
    ).fillna(0)
    mapped["share"] = pd.to_numeric(_series_or_default(raw_df, "share_count", "share", default=0), errors="coerce").fillna(
        0
    )
    mapped["duration"] = pd.to_numeric(_series_or_default(raw_df, "duration", default=0), errors="coerce").fillna(0)
    if "topic" in raw_df.columns:
        topic_series = raw_df["topic"]
    elif "category" in raw_df.columns:
        topic_series = raw_df["category"]
    else:
        topic_series = pd.Series(["other"] * len(raw_df), index=raw_df.index, dtype=object)
    mapped["topic"] = topic_series.map(lambda x: normalize_topic(str(x) if pd.notna(x) else ""))

    if "stance" in raw_df.columns:
        mapped["stance"] = raw_df["stance"].fillna("neutral").astype(str)
    else:
        mapped["stance"] = "neutral"
    mapped["emotion_score"] = pd.to_numeric(
        _series_or_default(raw_df, "emotion_score", default=3), errors="coerce"
    ).fillna(3)
    mapped["author_id"] = _series_or_default(raw_df, "author_id", default="")
    return _ensure_columns(mapped)


def parse_douyin_export(file_path: str | Path) -> pd.DataFrame:
    path = Path(file_path)
    if path.suffix.lower() == ".csv":
        raw_df = pd.read_csv(path)
    elif path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        raw_df = pd.DataFrame(data if isinstance(data, list) else data.get("items", []))
    else:
        raise ValueError("Only csv/json are currently supported for douyin parser.")

    if raw_df.empty:
        raise ValueError("文件为空或没有可解析的数据行")
    return _map_raw_douyin_dataframe(raw_df)


def parse_douyin_bytes(content: bytes, suffix: str) -> pd.DataFrame:
    suf = suffix.lower().lstrip(".")
    if suf == "csv":
        raw_df = read_csv_bytes(content)
    elif suf == "json":
        data = load_json_from_bytes(content)
        raw_df = pd.DataFrame(data if isinstance(data, list) else data.get("items", []))
    else:
        raise ValueError("抖音导出解析仅支持 .csv / .json")
    if raw_df.empty:
        raise ValueError("文件为空或没有可解析的数据行")
    return _map_raw_douyin_dataframe(raw_df)
