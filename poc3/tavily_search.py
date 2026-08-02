import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import sleep
from urllib.parse import urlparse

from requests.exceptions import RequestException
from tavily import TavilyClient
from tavily.errors import (
    BadRequestError,
    ForbiddenError,
    InvalidAPIKeyError,
    TimeoutError as TavilyTimeoutError,
    UsageLimitExceededError,
)

from .domain import SearchTimeLimit, TavilySearchDepth, TavilySearchTopic
from .search_models import SearchResult, WebSearchError


logger = logging.getLogger(__name__)


class TavilyWebSearchClient:
    """把 Tavily Search API 结果标准化为 SearchResult。"""

    def __init__(
        self,
        api_key: str,
        *,
        search_depth: TavilySearchDepth = "basic",
        topic: TavilySearchTopic = "general",
        timeout: int = 30,
        max_retries: int = 1,
        retry_delay: float = 1,
    ) -> None:
        clean_key = api_key.strip()
        if not clean_key:
            raise ValueError("Tavily API Key 不能为空")
        if search_depth not in {"basic", "advanced", "fast", "ultra-fast"}:
            raise ValueError("TAVILY_SEARCH_DEPTH 配置无效")
        if topic not in {"general", "news", "finance"}:
            raise ValueError("TAVILY_SEARCH_TOPIC 配置无效")
        if timeout <= 0:
            raise ValueError("WEB_SEARCH_TIMEOUT 必须大于 0")
        if max_retries < 0:
            raise ValueError("TAVILY_MAX_RETRIES 不能小于 0")
        if retry_delay < 0:
            raise ValueError("TAVILY_RETRY_DELAY 不能小于 0")

        self.search_depth = search_depth
        self.topic = topic
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client = TavilyClient(api_key=clean_key)

    def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        time_limit: SearchTimeLimit | None = None,
    ) -> list[SearchResult]:
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("搜索词不能为空")
        if not 1 <= max_results <= 10:
            raise ValueError("max_results 必须在 1 到 10 之间")

        logger.info(
            "Tavily search start query=%r max_results=%s time_limit=%s "
            "depth=%s topic=%s",
            clean_query,
            max_results,
            time_limit,
            self.search_depth,
            self.topic,
        )
        request: dict[str, object] = {
            "query": clean_query,
            "search_depth": self.search_depth,
            "topic": self.topic,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
            "timeout": self.timeout,
        }
        if time_limit is not None:
            request["time_range"] = time_limit

        response = self._search_with_retry(request, clean_query)

        retrieved_at = datetime.now(timezone.utc)
        normalized: list[SearchResult] = []
        seen_urls: set[str] = set()
        for item in response.get("results", []) if response else []:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            hostname = urlparse(url).hostname or "unknown"
            normalized.append(
                SearchResult(
                    title=str(item.get("title") or url).strip(),
                    url=url,
                    snippet=str(item.get("content") or "").strip(),
                    source=hostname.removeprefix("www."),
                    score=_parse_score(item.get("score")),
                    published_at=_parse_datetime(item.get("published_date")),
                    retrieved_at=retrieved_at,
                )
            )
            if len(normalized) >= max_results:
                break

        logger.info("Tavily search complete results=%s", len(normalized))
        return normalized

    def _search_with_retry(
        self,
        request: dict[str, object],
        clean_query: str,
    ) -> dict:
        total_attempts = self.max_retries + 1
        for attempt in range(1, total_attempts + 1):
            try:
                return self._client.search(**request)
            except (TavilyTimeoutError, RequestException) as exc:
                if attempt >= total_attempts:
                    logger.exception(
                        "Tavily transient failure exhausted retries query=%r "
                        "attempts=%s",
                        clean_query,
                        total_attempts,
                    )
                    if isinstance(exc, TavilyTimeoutError):
                        raise WebSearchError(
                            f"Tavily 搜索超时：每次等待 {self.timeout} 秒，"
                            f"共尝试 {total_attempts} 次。请稍后重试、增大 "
                            "WEB_SEARCH_TIMEOUT，或设置 "
                            "WEB_SEARCH_PROVIDER=ddgs。"
                        ) from exc
                    raise WebSearchError(
                        f"Tavily 临时网络故障，共尝试 {total_attempts} 次。"
                        "请稍后重试或设置 WEB_SEARCH_PROVIDER=ddgs。"
                    ) from exc

                logger.warning(
                    "Tavily transient failure, retrying query=%r "
                    "attempt=%s/%s error=%s delay=%ss",
                    clean_query,
                    attempt,
                    total_attempts,
                    type(exc).__name__,
                    self.retry_delay,
                )
                if self.retry_delay:
                    sleep(self.retry_delay)
            except InvalidAPIKeyError as exc:
                logger.error("Tavily authentication failed")
                raise WebSearchError(
                    "Tavily API Key 无效或已被撤销，请更新 .env 中的 "
                    "TAVILY_API_KEY。"
                ) from exc
            except UsageLimitExceededError as exc:
                logger.error("Tavily usage limit exceeded")
                raise WebSearchError(
                    "Tavily 搜索额度已用完，请检查账户额度或设置 "
                    "WEB_SEARCH_PROVIDER=ddgs。"
                ) from exc
            except (BadRequestError, ForbiddenError) as exc:
                logger.error(
                    "Tavily request rejected error=%s",
                    type(exc).__name__,
                )
                raise WebSearchError(
                    f"Tavily 拒绝了搜索请求：{type(exc).__name__}。"
                    "请检查搜索配置和账户权限。"
                ) from exc
            except Exception as exc:
                logger.exception("Tavily search failed query=%r", clean_query)
                raise WebSearchError(
                    f"外部搜索失败：{type(exc).__name__}"
                ) from exc

        raise AssertionError("Tavily retry loop ended unexpectedly")


def _parse_score(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
