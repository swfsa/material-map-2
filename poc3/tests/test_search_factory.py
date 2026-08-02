import pytest

import poc3.search_factory as search_factory
from poc3.config import ConfigurationError
from poc3.web_search import DDGSWebSearchClient


def test_creates_ddgs_fallback_without_tavily_key() -> None:
    client = search_factory.create_web_search_client("ddgs")

    assert isinstance(client, DDGSWebSearchClient)


def test_creates_tavily_client(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    captured: dict[str, object] = {}

    def fake_require_key() -> str:
        captured["key_requested"] = True
        return "test-key"

    def fake_client(api_key: str, **kwargs):
        captured["api_key"] = api_key
        captured["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(search_factory, "require_tavily_api_key", fake_require_key)
    monkeypatch.setattr(search_factory, "TavilyWebSearchClient", fake_client)

    client = search_factory.create_web_search_client("tavily")

    assert client is sentinel
    assert captured["key_requested"] is True
    assert captured["api_key"] == "test-key"
    assert captured["kwargs"] == {
        "search_depth": search_factory.TAVILY_SEARCH_DEPTH,
        "topic": search_factory.TAVILY_SEARCH_TOPIC,
        "timeout": search_factory.WEB_SEARCH_TIMEOUT,
        "max_retries": search_factory.TAVILY_MAX_RETRIES,
        "retry_delay": search_factory.TAVILY_RETRY_DELAY,
    }


def test_rejects_unknown_provider() -> None:
    with pytest.raises(ConfigurationError, match="tavily 或 ddgs"):
        search_factory.create_web_search_client("unknown")  # type: ignore[arg-type]
