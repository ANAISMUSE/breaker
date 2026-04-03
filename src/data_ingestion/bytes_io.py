"""从字节流读取 CSV / JSON，带常见中文编码回退。"""

from __future__ import annotations

import io
import json
from typing import Optional

import pandas as pd


def read_csv_bytes(content: bytes) -> pd.DataFrame:
    last: Optional[UnicodeDecodeError] = None
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return pd.read_csv(io.BytesIO(content), encoding=encoding)
        except UnicodeDecodeError as e:
            last = e
            continue
    if last is not None:
        try:
            return pd.read_csv(io.BytesIO(content), encoding="utf-8", errors="replace")
        except Exception:
            raise last from None
    raise ValueError("CSV 无法解析")


def load_json_from_bytes(content: bytes) -> object:
    text: Optional[str] = None
    if content.startswith(b"\xef\xbb\xbf"):
        text = content.decode("utf-8-sig")
    else:
        for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
    if text is None:
        text = content.decode("utf-8", errors="replace")
    return json.loads(text)
