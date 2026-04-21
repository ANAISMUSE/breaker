from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    inference_mode: str = os.getenv("INFERENCE_MODE", "remote")
    llm_provider: str = os.getenv("LLM_PROVIDER", "dashscope")
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    dashscope_base_url: str = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "qwen3-embedding-4b")
    multimodal_model: str = os.getenv("MULTIMODAL_MODEL", "qwen2.5-omni-7b")
    text_embedding_model: str = os.getenv("TEXT_EMBEDDING_MODEL", os.getenv("EMBEDDING_MODEL", "qwen3-embedding-4b"))
    multimodal_embedding_model: str = os.getenv(
        "MULTIMODAL_EMBEDDING_MODEL", os.getenv("EMBEDDING_MODEL", "qwen3-embedding-4b")
    )
    omni_model: str = os.getenv("OMNI_MODEL", os.getenv("MULTIMODAL_MODEL", "qwen2.5-omni-7b"))
    report_model: str = os.getenv("REPORT_MODEL", os.getenv("MULTIMODAL_MODEL", "qwen2.5-omni-7b"))
    llm_request_timeout_seconds: float = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "45"))
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "2"))
    llm_retry_backoff_seconds: float = float(os.getenv("LLM_RETRY_BACKOFF_SECONDS", "1.0"))
    local_openai_base_url: str = os.getenv("LOCAL_OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
    local_openai_api_key: str = os.getenv("LOCAL_OPENAI_API_KEY", "EMPTY")
    local_embedding_model: str = os.getenv("LOCAL_EMBEDDING_MODEL", "qwen3-embedding-4b")
    local_multimodal_model: str = os.getenv("LOCAL_MULTIMODAL_MODEL", "qwen2.5-omni-7b")
    lora_base_model: str = os.getenv("LORA_BASE_MODEL", os.getenv("LOCAL_MULTIMODAL_MODEL", "qwen2.5-omni-7b"))
    lora_adapter_path: str = os.getenv("LORA_ADAPTER_PATH", "")
    lora_enabled: bool = os.getenv("LORA_ENABLED", "false").lower() == "true"
    default_platform: str = os.getenv("DEFAULT_PLATFORM", "douyin")
    use_llm_scoring: bool = os.getenv("USE_LLM_SCORING", "false").lower() == "true"
    mediacrawler_project_dir: str = os.getenv("MEDIACRAWLER_PROJECT_DIR", "")
    mediacrawler_entry: str = os.getenv("MEDIACRAWLER_ENTRY", "main.py")
    enable_real_crawler: bool = os.getenv("ENABLE_REAL_CRAWLER", "false").lower() == "true"
    mediacrawler_command: str = os.getenv(
        "MEDIACRAWLER_COMMAND",
        "python {entry} --platform {platform} --keyword \"{keyword}\" --limit {limit} --output \"{output}\"",
    )
    mediacrawler_output_file: str = os.getenv("MEDIACRAWLER_OUTPUT_FILE", "data/mediacrawler_output.json")
    crawler_legal_ack: bool = os.getenv("CRAWLER_LEGAL_ACK", "false").lower() == "true"
    crawler_allowed_purposes: str = os.getenv(
        "CRAWLER_ALLOWED_PURPOSES",
        "academic_research,model_evaluation,teaching_demo",
    )
    app_secret: str = os.getenv("APP_SECRET", "change-me-in-env")
    mysql_url: str = os.getenv("MYSQL_URL", "")
    storage_backend: str = os.getenv("STORAGE_BACKEND", "sqlite")
    enable_cloud_monitor: bool = os.getenv("ENABLE_CLOUD_MONITOR", "false").lower() == "true"
    # 登录页（未登录时）：背景为合法 CSS background 值；可选本地图与半透明遮罩
    login_page_background: str = os.getenv(
        "LOGIN_PAGE_BACKGROUND",
        "linear-gradient(160deg, #eef2f7 0%, #dde4ef 48%, #e8edf5 100%)",
    )
    login_bg_image_path: str = os.getenv("LOGIN_BG_IMAGE_PATH", "").strip()
    login_bg_overlay: str = os.getenv("LOGIN_BG_OVERLAY", "").strip()

    def validate_runtime(self) -> None:
        mode = self.inference_mode.strip().lower()
        provider = self.llm_provider.strip().lower()
        if mode not in {"remote", "local"}:
            raise ValueError(f"Invalid INFERENCE_MODE={self.inference_mode!r}; expected 'remote' or 'local'.")
        if provider not in {"dashscope", "local"}:
            raise ValueError(f"Invalid LLM_PROVIDER={self.llm_provider!r}; expected 'dashscope' or 'local'.")
        if mode == "remote" and provider == "dashscope" and not self.dashscope_api_key.strip():
            raise ValueError(
                "DASHSCOPE_API_KEY is required when INFERENCE_MODE=remote and LLM_PROVIDER=dashscope. "
                "Please configure DASHSCOPE_API_KEY in .env or switch to local mode."
            )
        if self.lora_enabled and not self.lora_adapter_path.strip():
            raise ValueError("LORA_ADAPTER_PATH is required when LORA_ENABLED=true.")

    def active_local_chat_model(self) -> str:
        if self.lora_enabled and self.lora_adapter_path.strip():
            return self.lora_adapter_path.strip()
        return self.local_multimodal_model


settings = Settings()
