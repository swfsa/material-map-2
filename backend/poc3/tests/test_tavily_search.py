from collections.abc import Callable
from types import SimpleNamespace

import pytest
from tavily.errors import InvalidAPIKeyError, TimeoutError as TavilyTimeoutError

import poc3.tavily_search as tavily_search
from poc3.search_models import WebSearchError


def install_tavily_stub(
    monkeypatch: pytest.MonkeyPatch,
    outcomes: list[object],
) -> SimpleNamespace:
    state = SimpleNamespace(api_key=None, calls=[])
    remaining = list(outcomes)

    class StubTavilyClient:
        def __init__(self, api_key: str) -> None:
            state.api_key = api_key

        def search(self, **kwargs):
            state.calls.append(kwargs)
            outcome = remaining.pop(0)
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

    monkeypatch.setattr(tavily_search, "TavilyClient", StubTavilyClient)
    return state


def test_normalizes_results_and_sends_safe_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = install_tavily_stub(
        monkeypatch,
        [
            {
                "results": [
                    {
                        "title": "Oil news",
                        "url": "https://www.example.com/oil",
                        "content": "Supply summary",
                        "score": 0.91,
                        "published_date": "2026-07-28T10:00:00Z",
                    },
                    {
                        "title": "Duplicate",
                        "url": "https://www.example.com/oil",
                        "content": "Duplicate summary",
                        "score": 0.8,
                    },
                ]
            }
        ],
    )

    results = tavily_search.TavilyWebSearchClient(
        "test-key",
        search_depth="basic",
        topic="news",
        timeout=3,
    ).search("oil supply", max_results=3, time_limit="w")

    assert len(results) == 1
    assert results[0].source == "example.com"
    assert results[0].snippet == "Supply summary"
    assert results[0].score == 0.91
    assert results[0].published_at is not None
    assert state.calls == [
        {
            "query": "oil supply",
            "search_depth": "basic",
            "topic": "news",
            "max_results": 3,
            "include_answer": False,
            "include_raw_content": False,
            "timeout": 3,
            "time_range": "w",
        }
    ]


def test_wraps_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    install_tavily_stub(monkeypatch, [RuntimeError("provider down")])

    with caplog.at_level("ERROR", logger="mysql_demo2.tavily_search"):
        with pytest.raises(WebSearchError):
            tavily_search.TavilyWebSearchClient("test-key").search("oil")

    assert "Tavily search failed" in caplog.text


def test_retries_timeout_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    state = install_tavily_stub(
        monkeypatch,
        [
            TavilyTimeoutError(30),
            {
                "results": [
                    {
                        "title": "Recovered",
                        "url": "https://example.com/recovered",
                        "content": "Second attempt succeeded.",
                    }
                ]
            },
        ],
    )
    sleep_calls: list[float] = []
    fake_sleep: Callable[[float], None] = sleep_calls.append
    monkeypatch.setattr(tavily_search, "sleep", fake_sleep)

    with caplog.at_level("WARNING", logger="mysql_demo2.tavily_search"):
        results = tavily_search.TavilyWebSearchClient(
            "test-key",
            timeout=30,
            max_retries=1,
            retry_delay=0.5,
        ).search("oil")

    assert results[0].title == "Recovered"
    assert len(state.calls) == 2
    assert sleep_calls == [0.5]
    assert "retrying" in caplog.text


def test_reports_timeout_after_retry_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    state = install_tavily_stub(
        monkeypatch,
        [TavilyTimeoutError(30), TavilyTimeoutError(30)],
    )

    with caplog.at_level("ERROR", logger="mysql_demo2.tavily_search"):
        with pytest.raises(
            WebSearchError,
            match="每次等待 30 秒，共尝试 2 次",
        ):
            tavily_search.TavilyWebSearchClient(
                "test-key",
                timeout=30,
                max_retries=1,
                retry_delay=0,
            ).search("oil")

    assert len(state.calls) == 2


def test_does_not_retry_invalid_api_key(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    state = install_tavily_stub(
        monkeypatch,
        [InvalidAPIKeyError("invalid")],
    )

    with caplog.at_level("ERROR", logger="mysql_demo2.tavily_search"):
        with pytest.raises(WebSearchError, match="API Key 无效"):
            tavily_search.TavilyWebSearchClient(
                "test-key",
                max_retries=2,
            ).search("oil")

    assert len(state.calls) == 1


def test_rejects_empty_key() -> None:
    with pytest.raises(ValueError, match="API Key 不能为空"):
        tavily_search.TavilyWebSearchClient("  ")
