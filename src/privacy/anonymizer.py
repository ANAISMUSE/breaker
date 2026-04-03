import hashlib
import re
from typing import Any

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"1[3-9]\d{9}")

PII_KEYS = {"user_id", "author_id", "nickname", "phone", "email"}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


def _mask_text(text: str) -> str:
    text = EMAIL_RE.sub("[EMAIL_MASKED]", text)
    text = PHONE_RE.sub("[PHONE_MASKED]", text)
    return text


def anonymize_record(record: dict[str, Any]) -> dict[str, Any]:
    output = dict(record)
    for key in list(output.keys()):
        value = output.get(key)
        if value is None:
            continue
        if key in PII_KEYS:
            output[key] = f"anon_{_hash_text(str(value))}"
        elif isinstance(value, str):
            output[key] = _mask_text(value)
    return output
