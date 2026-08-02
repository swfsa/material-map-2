import os
from pathlib import Path
from typing import cast

from dotenv import load_dotenv

from .domain import TavilySearchDepth, TavilySearchTopic, WebSearchProvider


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
#读取并保存以下配置：
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"
#cast 只帮助静态类型检查，不会在运行时验证值。WEB_SEARCH_PROVIDER=abc 能完成 import，直到调用 [`create_web_search_client()` (line 20)](E:/code/poc3-1/poc3/search_factory.py:20) 才抛出 ConfigurationError
WEB_SEARCH_PROVIDER = cast(
    WebSearchProvider,
    os.getenv("WEB_SEARCH_PROVIDER", "tavily").strip().lower() or "tavily",
)
TAVILY_SEARCH_DEPTH = cast(
    TavilySearchDepth,
    os.getenv("TAVILY_SEARCH_DEPTH", "basic").strip().lower() or "basic",
)
TAVILY_SEARCH_TOPIC = cast(
    TavilySearchTopic,
    os.getenv("TAVILY_SEARCH_TOPIC", "general").strip().lower() or "general",
)
WEB_SEARCH_REGION = os.getenv("WEB_SEARCH_REGION", "wt-wt").strip() or "wt-wt"
WEB_SEARCH_SAFESEARCH = (
    os.getenv("WEB_SEARCH_SAFESEARCH", "moderate").strip() or "moderate"
)
WEB_SEARCH_BACKEND = os.getenv("WEB_SEARCH_BACKEND", "auto").strip() or "auto"

#转换数值：数值字符串非法时，模块导入阶段就会抛出 RuntimeError。
try:
    WEB_SEARCH_TIMEOUT = int(os.getenv("WEB_SEARCH_TIMEOUT", "30"))
except ValueError as exc:
    raise RuntimeError("WEB_SEARCH_TIMEOUT 必须是整数秒数") from exc

try:
    TAVILY_MAX_RETRIES = int(os.getenv("TAVILY_MAX_RETRIES", "1"))
except ValueError as exc:
    raise RuntimeError("TAVILY_MAX_RETRIES 必须是整数") from exc

try:
    TAVILY_RETRY_DELAY = float(os.getenv("TAVILY_RETRY_DELAY", "1"))
except ValueError as exc:
    raise RuntimeError("TAVILY_RETRY_DELAY 必须是秒数") from exc


class ConfigurationError(RuntimeError):
    """本机必需配置缺失。"""


def require_database_url() -> str:
    """返回数据库 URL，但绝不把值写入日志或异常。
    调用时检查 DATABASE_URL 是否为空；
    但检查的是 import 时已经保存的全局变量；
    import 后再修改环境变量，它不会自动重新读取。
    """
    if not DATABASE_URL:
        raise ConfigurationError(
            "未检测到 DATABASE_URL。请在项目根目录 .env 中配置 MySQL 连接。"
        )
    return DATABASE_URL


def require_tavily_api_key() -> str:
    """返回 Tavily Key，但绝不把值写入日志或异常。
    调用时才读取 TAVILY_API_KEY；
    调用时检查是否为空
    缺失时抛出 ConfigurationError；
    因为每次调用都执行 os.getenv()，所以可以看到 import 后设置的新值。
    """
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise ConfigurationError(
            "当前搜索供应商为 Tavily，但未检测到 TAVILY_API_KEY。"
            "请在项目根目录 .env 中填写该配置。"
        )
    return api_key
