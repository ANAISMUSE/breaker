from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "dashscope")
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    dashscope_base_url: str = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
    multimodal_model: str = os.getenv("MULTIMODAL_MODEL", "qwen-vl-plus")
    local_embedding_model: str = os.getenv("LOCAL_EMBEDDING_MODEL", "qwen3-embedding-4b")
    local_multimodal_model: str = os.getenv("LOCAL_MULTIMODAL_MODEL", "qwen2.5-omni-7b")
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


settings = Settings()
