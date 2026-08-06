import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from ddgs import DDGS

from .domain import SearchTimeLimit
from .search_models import SearchResult, WebSearchError


logger = logging.getLogger(__name__)


class DDGSWebSearchClient:
    """把 DDGS 元搜索结果标准化为 SearchResult。"""

    def __init__(
        self,
        *,
        region: str = "wt-wt",
        safesearch: str = "moderate",
        backend: str = "auto",
        timeout: int = 10,
    ) -> None:
        self.region = region
        self.safesearch = safesearch
        self.backend = backend
        self.timeout = timeout

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
            "DDGS search start query=%r max_results=%s time_limit=%s backend=%s",
            clean_query,
            max_results,
            time_limit,
            self.backend,
        )
        try:
            raw_results = DDGS(timeout=self.timeout).text(
                clean_query,
                region=self.region,
                safesearch=self.safesearch,
                timelimit=time_limit,
                max_results=max_results,
                backend=self.backend,
            )
        except Exception as exc:
            logger.exception("DDGS search failed query=%r", clean_query)
            raise WebSearchError(f"外部搜索失败：{type(exc).__name__}") from exc
        #记录搜索时间
        retrieved_at = datetime.now(timezone.utc)
        normalized: list[SearchResult] = []
        #防止重复 URL
        seen_urls: set[str] = set()
        for item in raw_results or []:
            url = str(item.get("href") or item.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            hostname = urlparse(url).hostname or "unknown"
            normalized.append(
                SearchResult(
                    title=str(item.get("title") or url).strip(),
                    url=url,
                    snippet=str(item.get("body") or item.get("snippet") or "").strip(),
                    source=hostname.removeprefix("www."),
                    published_at=_parse_datetime(item.get("date")),
                    retrieved_at=retrieved_at,
                )
            )
            if len(normalized) >= max_results:
                break

        logger.info("DDGS search complete results=%s", len(normalized))
        return normalized


def _parse_datetime(value: object) -> datetime | None:
    """
    把搜索结果中的日期：字符串->datetime对象
    :param value:
    :return:
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
