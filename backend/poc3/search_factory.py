from .config import (
    TAVILY_MAX_RETRIES,
    TAVILY_RETRY_DELAY,
    TAVILY_SEARCH_DEPTH,
    TAVILY_SEARCH_TOPIC,
    WEB_SEARCH_BACKEND,
    WEB_SEARCH_PROVIDER,
    WEB_SEARCH_REGION,
    WEB_SEARCH_SAFESEARCH,
    WEB_SEARCH_TIMEOUT,
    ConfigurationError,
    require_tavily_api_key,
)
from .domain import WebSearchProvider
from .search_models import WebSearchClient
from .tavily_search import TavilyWebSearchClient
from .web_search import DDGSWebSearchClient


def create_web_search_client(
    provider: WebSearchProvider | None = None,
) -> WebSearchClient:
    """根据配置创建搜索客户端；Tavily 默认，DDGS 可作为备用。"""
    selected = provider or WEB_SEARCH_PROVIDER
    if selected == "tavily":
        return TavilyWebSearchClient(
            require_tavily_api_key(),
            search_depth=TAVILY_SEARCH_DEPTH,
            topic=TAVILY_SEARCH_TOPIC,
            timeout=WEB_SEARCH_TIMEOUT,
            max_retries=TAVILY_MAX_RETRIES,
            retry_delay=TAVILY_RETRY_DELAY,
        )
    if selected == "ddgs":
        return DDGSWebSearchClient(
            region=WEB_SEARCH_REGION,
            safesearch=WEB_SEARCH_SAFESEARCH,
            backend=WEB_SEARCH_BACKEND,
            timeout=WEB_SEARCH_TIMEOUT,
        )
    raise ConfigurationError(
        f"WEB_SEARCH_PROVIDER={selected!r} 无效，只能使用 tavily 或 ddgs。"
    )
