import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DEEPSEEK_MODEL = (
    os.getenv("DEEPSEEK_MODEL", "deepseek:deepseek-v4-pro").strip()
    or "deepseek:deepseek-v4-pro"
)


class ConfigurationError(RuntimeError):
    """Raised when a required local setting is missing."""


def require_deepseek_api_key() -> str:
    """Return the configured key or explain how to configure it."""
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ConfigurationError(
            "未检测到 DEEPSEEK_API_KEY。请将项目根目录的 .env.example "
            "复制为 .env，并填写你的 DeepSeek API Key。"
        )
    return api_key

def require_database_url() -> str:
    """返回数据库 URL，但绝不把值写入日志或异常。"""
    if not DATABASE_URL:
        raise ConfigurationError(
            "未检测到 DATABASE_URL。请在项目根目录 .env 中配置 MySQL 连接。"
        )
    return DATABASE_URL
