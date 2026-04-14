from __future__ import annotations

import json
import unittest

from src.data_ingestion.import_service import import_bytes


class ImportServicePhase2Tests(unittest.TestCase):
    def test_detect_xiaohongshu_and_filter_invalid_rows(self) -> None:
        payload = [
            {
                "note_id": "xhs_1",
                "title": "露营装备",
                "liked_count": 12,
                "comment_count": 2,
                "time": "2026-04-14 10:00:00",
                "topic": "科技",
            },
            {
                "note_id": "xhs_2",
                "title": "",
                "liked_count": 1,
                "comment_count": 0,
                "time": "",
            },
        ]
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        result = import_bytes(content, "xhs.json", "auto")
        self.assertEqual(result.detected_platform, "xiaohongshu")
        self.assertEqual(result.invalid_row_count, 1)
        self.assertEqual(len(result.dataframe), 1)

    def test_detect_weibo(self) -> None:
        payload = [
            {
                "mblogid": "wb_1",
                "text_raw": "今天天气不错",
                "attitudes_count": 3,
                "comments_count": 1,
                "reposts_count": 0,
                "created_at": "2026-04-13 08:30:00",
            }
        ]
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        result = import_bytes(content, "weibo.json", "auto")
        self.assertEqual(result.detected_platform, "weibo")
        self.assertEqual(result.invalid_row_count, 0)
        self.assertEqual(len(result.dataframe), 1)


if __name__ == "__main__":
    unittest.main()
