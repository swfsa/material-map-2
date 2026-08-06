from types import SimpleNamespace

import pytest

import poc3.web_search as web_search
from poc3.search_models import WebSearchError


def install_ddgs_stub(
    monkeypatch: pytest.MonkeyPatch,
    outcome: object,
) -> SimpleNamespace:
    state = SimpleNamespace(timeout=None, calls=[])

    class StubDDGS:
        def __init__(self, *, timeout: int) -> None:
            state.timeout = timeout

        def text(self, *args, **kwargs):
            state.calls.append((args, kwargs))
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

    monkeypatch.setattr(web_search, "DDGS", StubDDGS)
    return state


def test_normalizes_and_deduplicates_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = install_ddgs_stub(
        monkeypatch,
        [
            {
                "title": "Result A",
                "href": "https://example.com/a",
                "body": "Summary A",
            },
            {
                "title": "Duplicate",
                "href": "https://example.com/a",
                "body": "Duplicate summary",
            },
            {
                "title": "Result B",
                "href": "https://news.example.org/b",
                "body": "Summary B",
            },
        ],
    )

    results = web_search.DDGSWebSearchClient(timeout=1).search(
        "oil",
        max_results=3,
    )

    assert len(results) == 2
    assert results[0].source == "example.com"
    assert results[1].url == "https://news.example.org/b"
    assert results[0].retrieved_at is not None
    assert state.timeout == 1
    assert len(state.calls) == 1


def test_wraps_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    install_ddgs_stub(monkeypatch, RuntimeError("provider down"))

    with caplog.at_level("ERROR", logger="mysql_demo2.web_search"):
        with pytest.raises(WebSearchError):
            web_search.DDGSWebSearchClient(timeout=1).search("oil")

    assert "DDGS search failed" in caplog.text
