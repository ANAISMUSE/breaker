from src.config.settings import settings
from src.llm.gateway import extract_json_payload
from src.llm import get_llm_provider


def test_local_provider_selection() -> None:
    settings.llm_provider = "local"
    provider = get_llm_provider()
    health = provider.health()
    assert health.provider == "local"
    assert health.ok is False


def test_dashscope_provider_selection() -> None:
    settings.llm_provider = "dashscope"
    provider = get_llm_provider()
    health = provider.health()
    assert health.provider == "dashscope"
    assert isinstance(health.ok, bool)


def test_extract_json_payload_handles_markdown_block() -> None:
    raw = """```json
    {"status":"ok","message":"ready"}
    ```"""
    parsed = extract_json_payload(raw)
    assert isinstance(parsed, dict)
    assert parsed["status"] == "ok"


def test_extract_json_payload_returns_none_when_invalid() -> None:
    assert extract_json_payload("not a json payload") is None


def test_validate_runtime_requires_dashscope_key_in_remote_mode() -> None:
    old_mode = settings.inference_mode
    old_provider = settings.llm_provider
    old_key = settings.dashscope_api_key
    try:
        settings.inference_mode = "remote"
        settings.llm_provider = "dashscope"
        settings.dashscope_api_key = ""
        raised = False
        try:
            settings.validate_runtime()
        except ValueError:
            raised = True
        assert raised is True
    finally:
        settings.inference_mode = old_mode
        settings.llm_provider = old_provider
        settings.dashscope_api_key = old_key


def test_validate_runtime_requires_lora_adapter_when_enabled() -> None:
    old_enabled = settings.lora_enabled
    old_adapter = settings.lora_adapter_path
    try:
        settings.lora_enabled = True
        settings.lora_adapter_path = ""
        raised = False
        try:
            settings.validate_runtime()
        except ValueError:
            raised = True
        assert raised is True
    finally:
        settings.lora_enabled = old_enabled
        settings.lora_adapter_path = old_adapter


def test_active_local_chat_model_prefers_lora_adapter() -> None:
    old_enabled = settings.lora_enabled
    old_adapter = settings.lora_adapter_path
    old_local_model = settings.local_multimodal_model
    try:
        settings.local_multimodal_model = "base-model"
        settings.lora_enabled = True
        settings.lora_adapter_path = "adapter-model"
        assert settings.active_local_chat_model() == "adapter-model"
        settings.lora_enabled = False
        assert settings.active_local_chat_model() == "base-model"
    finally:
        settings.lora_enabled = old_enabled
        settings.lora_adapter_path = old_adapter
        settings.local_multimodal_model = old_local_model
