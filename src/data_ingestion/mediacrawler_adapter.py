from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

import pandas as pd

from src.config.settings import settings
from src.data_ingestion.douyin_parser import parse_douyin_export


def _demo_fallback(keyword: str, limit: int) -> pd.DataFrame:
    # Demo fallback: use local sample to emulate crawler output shape.
    sample = Path("data/demo_douyin_export.json")
    if sample.exists():
        df = parse_douyin_export(sample)
        if keyword:
            df = df[df["text"].fillna("").str.contains(keyword, case=False, regex=False)]
        return df.head(limit).reset_index(drop=True)
    return pd.DataFrame()


def crawl_public_data_with_meta(platform: str, keyword: str = "", limit: int = 50) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    MediaCrawler 适配入口（演示/可选外接）。

    合规说明：本项目不在代码层实现验证码绕过、指纹对抗、多账号轮换等高风险能力。
    启用真实外接前须自行完成平台协议与《个人信息保护法》等合规评估；详见 README。
    """
    if platform != "douyin":
        raise ValueError("Demo adapter currently supports douyin only.")

    if settings.enable_cloud_monitor and settings.enable_real_crawler and settings.mediacrawler_project_dir:
        out_file = Path(settings.mediacrawler_output_file)
        if not out_file.is_absolute():
            out_file = Path.cwd() / out_file
        out_file.parent.mkdir(parents=True, exist_ok=True)
        cmd = settings.mediacrawler_command.format(
            entry=settings.mediacrawler_entry,
            platform=platform,
            keyword=keyword,
            limit=limit,
            output=str(out_file),
        )
        try:
            subprocess.run(
                cmd,
                cwd=settings.mediacrawler_project_dir,
                check=True,
                capture_output=True,
                text=True,
                shell=True,
            )
            if out_file.exists():
                raw = json.loads(out_file.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and "items" in raw:
                    raw = raw["items"]
                tmp = Path("data/mediacrawler_tmp.json")
                tmp.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
                return parse_douyin_export(tmp).head(limit).reset_index(drop=True), {
                    "mode": "real",
                    "degraded": False,
                    "reason": "",
                }
        except Exception as exc:
            # Fall through to demo fallback to keep UX stable.
            return _demo_fallback(keyword, limit), {
                "mode": "demo",
                "degraded": True,
                "reason": f"real adapter failed: {exc.__class__.__name__}",
            }

    reason = "cloud monitor disabled or adapter not configured"
    return _demo_fallback(keyword, limit), {
        "mode": "demo",
        "degraded": False,
        "reason": reason,
    }


def crawl_public_data(platform: str, keyword: str = "", limit: int = 50) -> pd.DataFrame:
    df, _ = crawl_public_data_with_meta(platform=platform, keyword=keyword, limit=limit)
    return df
