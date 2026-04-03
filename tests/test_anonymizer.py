from src.privacy.anonymizer import anonymize_record


def test_anonymize_record_masks_pii() -> None:
    out = anonymize_record(
        {
            "user_id": "alice",
            "text": "联系我 13812345678 或者 test@example.com",
        }
    )
    assert out["user_id"].startswith("anon_")
    assert "[PHONE_MASKED]" in out["text"]
    assert "[EMAIL_MASKED]" in out["text"]
