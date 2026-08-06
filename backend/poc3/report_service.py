"""Reusable orchestration for one deterministic EIA energy briefing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from .deps import AppDeps
from .energy_analysis import (
    EnergyMarketAnalysis,
    EnergySeriesRepository,
    analyze_energy_market,
)
from .energy_registry import DEFAULT_BRIEFING_INDICATORS
from .report import EnergyNarrative, ReportIR
from .report_builder import build_energy_report


@dataclass(frozen=True)
class GeneratedEnergyReport:
    report_ir: ReportIR
    analysis: EnergyMarketAnalysis
    narrative: EnergyNarrative


def generate_energy_report(
    question: str,
    *,
    analysis_repository: EnergySeriesRepository,
    agent_deps: AppDeps,
    model: Any,
    indicator_ids: list[str] | tuple[str, ...] = DEFAULT_BRIEFING_INDICATORS,
    start_date: date | None = None,
    end_date: date | None = None,
    agent_instance: Any = None,
) -> GeneratedEnergyReport:
    """Analyze first, then let the Agent explain the frozen calculation result."""

    if not question.strip():
        raise ValueError("question 不能为空")
    effective_end = end_date or date.today()
    effective_start = start_date or (effective_end - timedelta(days=365))
    if effective_start > effective_end:
        raise ValueError("start_date 不能晚于 end_date")

    analysis = analyze_energy_market(
        analysis_repository,
        indicator_ids,
        start_date=effective_start,
        end_date=effective_end,
    )
    if agent_instance is None:
        from .agent import agent as agent_instance

    prompt = (
        f"用户问题：{question.strip()}\n\n"
        "以下 JSON 是 Python 分析器的最终计算结果。不得改变其中的数值、单位、"
        "时间窗和风险规则，只负责解释并形成简报文字。\n"
        f"{analysis.model_dump_json(indent=2)}"
    )
    result = agent_instance.run_sync(
        prompt,
        deps=agent_deps,
        model=model,
    )
    narrative = EnergyNarrative.model_validate(result.output)
    return GeneratedEnergyReport(
        report_ir=build_energy_report(analysis, narrative),
        analysis=analysis,
        narrative=narrative,
    )
