from datetime import datetime, timezone
from types import SimpleNamespace

from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from poc3.agent import agent
from poc3.deps import AppDeps
from poc3.report import EnergyNarrative
from poc3.search_models import SearchResult


class FakeMaterialRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def query_material(self, sub_category, **kwargs):
        self.calls.append({"sub_category": sub_category, **kwargs})
        return [
            SimpleNamespace(
                record_id="oil-1",
                sub_category="crude_oil",
                period=datetime(2026, 7, 17),
                value=80.77,
                unit="USD/barrel",
                region="US-OK-CUSHING",
                source="eia",
                source_url="https://example.com/internal",
                confidence="official_periodic",
                fetched_at=datetime(2026, 7, 24),
            )
        ]


class FakeWebSearchClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def search(self, query, *, max_results=5, time_limit=None):
        self.calls.append(
            {
                "query": query,
                "max_results": max_results,
                "time_limit": time_limit,
            }
        )
        return [
            SearchResult(
                title="External oil report",
                url="https://example.org/oil",
                snippet="Supply risk summary",
                source="example.org",
                published_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
                retrieved_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            )
        ]


def test_offline_agent_calls_internal_and_external_tools() -> None:
    repository = FakeMaterialRepository()
    search_client = FakeWebSearchClient()
    deps = AppDeps(
        material_repo=repository,
        web_search_client=search_client,
    )
    output = {
        "summary": "Validated without network or a paid model.",
        "trend_commentary": "Internal and external tools were called.",
        "risk_commentary": "No additional risk was asserted.",
        "recommendations": ["Keep evidence URLs."],
        "external_evidence": [
            {
                "source_type": "external",
                "title": "External oil report",
                "source_name": "example.org",
                "summary": "Supply risk summary.",
                "url": "https://example.org/oil",
                "data_time": "2026-07-20T00:00:00",
                "retrieved_at": "2026-07-29T00:00:00",
            }
        ],
        "conflicts": [],
    }

    result = agent.run_sync(
        "Use both tools.",
        deps=deps,
        model=TestModel(
            call_tools=["query_material", "web_search"],
            custom_output_args=output,
        ),
    )

    assert isinstance(result.output, EnergyNarrative)
    assert len(repository.calls) == 1
    assert len(search_client.calls) == 1
    assert result.output.external_evidence[0].url == "https://example.org/oil"


def test_agent_recovers_after_two_invalid_report_outputs() -> None:
    attempts = 0
    valid_output = {
        "summary": "The third structured output is valid.",
        "trend_commentary": "Output validation retries are isolated.",
        "risk_commentary": "No new risk.",
        "recommendations": ["Keep the complete narrative contract."],
        "external_evidence": [],
        "conflicts": [],
    }

    def model_function(
        _messages: list[object],
        agent_info: AgentInfo,
    ) -> ModelResponse:
        nonlocal attempts
        attempts += 1
        output_tool = agent_info.output_tools[0]
        output = {"summary": "Incomplete narrative"} if attempts < 3 else valid_output
        return ModelResponse(
            parts=[ToolCallPart(tool_name=output_tool.name, args=output)]
        )

    deps = AppDeps(
        material_repo=FakeMaterialRepository(),
        web_search_client=FakeWebSearchClient(),
    )
    result = agent.run_sync(
        "Return the report directly.",
        deps=deps,
        model=FunctionModel(model_function),
    )

    assert attempts == 3
    assert result.output.summary == "The third structured output is valid."
