from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from .domain import SearchTimeLimit


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source: str | None = None
    score: float | None = None
    published_at: datetime | None = None
    retrieved_at: datetime


class WebSearchError(RuntimeError):
    """外部搜索服务无法返回可用结果。"""


@runtime_checkable
class WebSearchClient(Protocol):
    def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        time_limit: SearchTimeLimit | None = None,
    ) -> list[SearchResult]: ...
