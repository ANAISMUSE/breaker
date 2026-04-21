from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

import pandas as pd

from src.config.settings import settings
from src.data_ingestion.douyin_parser import parse_douyin_export
from src.data_ingestion.import_service import (
    _map_raw_weibo_dataframe,
    _map_raw_xiaohongshu_dataframe,
    ensure_standard_dataframe,
)

_SUPPORTED_PLATFORMS = {"douyin", "xiaohongshu", "weibo", "bilibili", "kuaishou"}


def _allowed_purposes() -> set[str]:
    raw = settings.crawler_allowed_purposes or ""
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _real_mode_gate_reason() -> str | None:
    if not settings.enable_cloud_monitor:
        return "ENABLE_CLOUD_MONITOR is false"
    if not settings.enable_real_crawler:
        return "ENABLE_REAL_CRAWLER is false"
    if not settings.crawler_legal_ack:
        return "CRAWLER_LEGAL_ACK is false"
    if not settings.mediacrawler_project_dir:
        return "MEDIACRAWLER_PROJECT_DIR is empty"
    return None


def _demo_fallback(platform: str, keyword: str, limit: int) -> pd.DataFrame:
    # Demo fallback: use local sample to emulate crawler output shape.
    sample = Path("data/demo_douyin_export.json")
    if sample.exists():
        df = parse_douyin_export(sample)
        df["platform"] = platform
        if keyword:
            df = df[df["text"].fillna("").str.contains(keyword, case=False, regex=False)]
        return df.head(limit).reset_index(drop=True)
    return pd.DataFrame()


def _parse_real_output(platform: str, raw: object) -> pd.DataFrame:
    if isinstance(raw, dict) and "items" in raw:
        raw = raw["items"]
    rows = raw if isinstance(raw, list) else []
    df_raw = pd.DataFrame(rows)
    if df_raw.empty:
        return pd.DataFrame()
    if platform == "douyin":
        tmp = Path("data/mediacrawler_tmp_douyin.json")
        tmp.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        return parse_douyin_export(tmp)
    if platform == "xiaohongshu":
        return _map_raw_xiaohongshu_dataframe(df_raw)
    if platform == "weibo":
        return _map_raw_weibo_dataframe(df_raw)
    # bilibili/kuaishou currently mapped to standard schema with platform override.
    if "platform" not in df_raw.columns:
        df_raw["platform"] = platform
    mapped = ensure_standard_dataframe(df_raw)
    mapped["platform"] = platform
    return mapped


def crawl_public_data_with_meta(
    platform: str,
    keyword: str = "",
    limit: int = 50,
    purpose: str = "academic_research",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    MediaCrawler 适配入口（演示/可选外接）。

    合规说明：本项目不在代码层实现验证码绕过、指纹对抗、多账号轮换等高风险能力。
    启用真实外接前须自行完成平台协议与《个人信息保护法》等合规评估；详见 README。
    """
    if platform not in _SUPPORTED_PLATFORMS:
        raise ValueError(f"unsupported platform: {platform}")

    gate_reason = _real_mode_gate_reason()
    purpose_normalized = (purpose or "").strip().lower()
    purposes = _allowed_purposes()
    purpose_allowed = bool(purpose_normalized) and (not purposes or purpose_normalized in purposes)

    if gate_reason is None and not purpose_allowed:
        reason = (
            f"purpose '{purpose_normalized or 'empty'}' not allowed; "
            f"allowed: {', '.join(sorted(purposes)) or 'none configured'}"
        )
        return _demo_fallback(platform, keyword, limit), {
            "mode": "demo",
            "degraded": True,
            "reason": reason,
            "legal_ack": settings.crawler_legal_ack,
            "compliance_gate_reason": reason,
            "purpose": purpose_normalized,
            "purpose_allowed": False,
        }

    if gate_reason is None:
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
                parsed = _parse_real_output(platform, raw)
                return parsed.head(limit).reset_index(drop=True), {
                    "mode": "real",
                    "degraded": False,
                    "reason": "",
                    "legal_ack": settings.crawler_legal_ack,
                    "compliance_gate_reason": "",
                    "purpose": purpose_normalized,
                    "purpose_allowed": True,
                }
        except Exception as exc:
            # Fall through to demo fallback to keep UX stable.
            return _demo_fallback(platform, keyword, limit), {
                "mode": "demo",
                "degraded": True,
                "reason": f"real adapter failed: {exc.__class__.__name__}",
                "legal_ack": settings.crawler_legal_ack,
                "compliance_gate_reason": "",
                "purpose": purpose_normalized,
                "purpose_allowed": purpose_allowed,
            }

    reason = gate_reason or "cloud monitor disabled or adapter not configured"
    return _demo_fallback(platform, keyword, limit), {
        "mode": "demo",
        "degraded": False,
        "reason": reason,
        "legal_ack": settings.crawler_legal_ack,
        "compliance_gate_reason": reason,
        "purpose": purpose_normalized,
        "purpose_allowed": purpose_allowed,
    }


def crawl_public_data(platform: str, keyword: str = "", limit: int = 50, purpose: str = "academic_research") -> pd.DataFrame:
    df, _ = crawl_public_data_with_meta(platform=platform, keyword=keyword, limit=limit, purpose=purpose)
    return df
