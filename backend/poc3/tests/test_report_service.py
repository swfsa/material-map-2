from datetime import datetime, timedelta

from pydantic_ai.models.test import TestModel

from poc3.agent import agent
from poc3.deps import AppDeps
from poc3.models import MaterialRecord
from poc3.report import KpiGridBlock
from poc3.report_service import generate_energy_report

from .test_agent_tools import FakeMaterialRepository, FakeWebSearchClient


class FakeEnergyRepository:
    def query_energy_series(self, indicator, **_kwargs):
        start = datetime(2026, 1, 1)
        return [
            MaterialRecord(
                record_id=f"wti-{index}",
                category="energy",
                sub_category=indicator.sub_category,
                region=indicator.region,
                metric_type=indicator.metric_type,
                value=70.0 + index * 0.2,
                unit=indicator.unit,
                period=start + timedelta(days=index),
                source="eia",
            )
            for index in range(40)
        ]


def test_service_analyzes_before_agent_and_builds_numeric_report() -> None:
    deps = AppDeps(
        material_repo=FakeMaterialRepository(),
        web_search_client=FakeWebSearchClient(),
    )
    generated = generate_energy_report(
        "分析 WTI",
        analysis_repository=FakeEnergyRepository(),
        agent_deps=deps,
        model=TestModel(
            custom_output_args={
                "summary": "WTI 市场摘要。",
                "trend_commentary": "WTI 趋势解释。",
                "risk_commentary": "WTI 风险解释。",
                "recommendations": ["持续跟踪。"],
                "external_evidence": [],
                "conflicts": [],
            }
        ),
        indicator_ids=["wti_spot"],
        agent_instance=agent,
    )

    assert generated.analysis.indicators[0].latest_value == 77.8
    kpi = next(
        block
        for block in generated.report_ir.blocks
        if isinstance(block, KpiGridBlock)
    )
    assert kpi.data.items[0].value == 77.8
    assert generated.narrative.summary == "WTI 市场摘要。"
