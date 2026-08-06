"""Assemble validated numerical analysis and LLM prose into ReportIR blocks."""

from __future__ import annotations

from .energy_analysis import EnergyMarketAnalysis, EnergyRiskSignal
from .report import (
    CalloutBlock,
    CalloutData,
    EnergyNarrative,
    HeadingBlock,
    HeadingData,
    KpiGridBlock,
    KpiGridData,
    KpiItem,
    KpiStatus,
    ParagraphBlock,
    ParagraphData,
    ReportBlock,
    ReportIR,
    RiskSeverity,
    TableBlock,
    TableColumn,
    TableData,
)


_SEVERITY_ORDER: dict[RiskSeverity, int] = {
    "info": 0,
    "watch": 1,
    "warning": 2,
    "critical": 3,
}


def build_energy_report(
    analysis: EnergyMarketAnalysis,
    narrative: EnergyNarrative,
) -> ReportIR:
    blocks: list[ReportBlock] = [
        HeadingBlock(
            type="heading",
            data=HeadingData(
                text="EIA 能源市场状态、趋势、波动与风险简报",
                level=1,
            ),
        ),
        ParagraphBlock(
            type="paragraph",
            data=ParagraphData(
                text=narrative.summary,
                evidence_ids=_all_evidence_ids(analysis),
            ),
        ),
        HeadingBlock(type="heading", data=HeadingData(text="一、市场状态")),
        KpiGridBlock(
            type="kpiGrid",
            data=KpiGridData(
                items=[
                    KpiItem(
                        label=item.display_name,
                        value=round(item.latest_value, 4),
                        unit=item.unit,
                        change=_round_optional(item.change_30d_percent),
                        change_period="30d",
                        trend=item.trend,
                        status=_indicator_status(item.indicator_id, analysis.risks),
                        as_of=item.period_end,
                        source_record_ids=item.evidence_record_ids,
                    )
                    for item in analysis.indicators
                ]
            ),
        ),
        HeadingBlock(type="heading", data=HeadingData(text="二、趋势与波动")),
        TableBlock(
            type="table",
            data=TableData(
                title="能源指标统计",
                columns=[
                    TableColumn(key="indicator", label="指标"),
                    TableColumn(key="latest", label="最新值"),
                    TableColumn(key="unit", label="单位"),
                    TableColumn(key="change_7d", label="7日变化", unit="%"),
                    TableColumn(key="change_30d", label="30日变化", unit="%"),
                    TableColumn(key="ma_30d", label="30日均值"),
                    TableColumn(key="volatility", label="30日年化波动率", unit="%"),
                    TableColumn(key="percentile", label="窗口分位数", unit="%"),
                    TableColumn(key="drawdown", label="最大回撤", unit="%"),
                    TableColumn(key="trend", label="趋势"),
                ],
                rows=[
                    {
                        "indicator": item.display_name,
                        "latest": round(item.latest_value, 4),
                        "unit": item.unit,
                        "change_7d": _round_optional(item.change_7d_percent),
                        "change_30d": _round_optional(item.change_30d_percent),
                        "ma_30d": _round_optional(item.moving_average_30d, digits=4),
                        "volatility": _round_optional(
                            item.annualized_volatility_30d_percent
                        ),
                        "percentile": round(item.historical_percentile, 2),
                        "drawdown": _round_optional(item.max_drawdown_percent),
                        "trend": item.trend,
                    }
                    for item in analysis.indicators
                ],
            ),
        ),
        ParagraphBlock(
            type="paragraph",
            data=ParagraphData(
                text=narrative.trend_commentary,
                evidence_ids=_all_evidence_ids(analysis),
            ),
        ),
        HeadingBlock(type="heading", data=HeadingData(text="三、风险监测")),
    ]

    if analysis.risks:
        blocks.extend(_risk_block(signal) for signal in analysis.risks)
    else:
        blocks.append(
            CalloutBlock(
                type="callout",
                data=CalloutData(
                    title="未触发量化风险规则",
                    text="当前请求时间窗内未触发异常、过期、波动率或回撤规则。",
                    severity="info",
                    evidence_ids=_all_evidence_ids(analysis),
                ),
            )
        )
    blocks.append(
        ParagraphBlock(
            type="paragraph",
            data=ParagraphData(
                text=narrative.risk_commentary,
                evidence_ids=_all_evidence_ids(analysis),
            ),
        )
    )

    if narrative.recommendations:
        blocks.extend(
            [
                HeadingBlock(
                    type="heading",
                    data=HeadingData(text="四、跟踪建议"),
                ),
                TableBlock(
                    type="table",
                    data=TableData(
                        columns=[TableColumn(key="recommendation", label="建议")],
                        rows=[
                            {"recommendation": recommendation}
                            for recommendation in narrative.recommendations
                        ],
                    ),
                ),
            ]
        )

    if narrative.external_evidence:
        blocks.extend(
            [
                HeadingBlock(
                    type="heading",
                    data=HeadingData(text="五、外部证据"),
                ),
                TableBlock(
                    type="table",
                    data=TableData(
                        columns=[
                            TableColumn(key="evidence_id", label="证据ID"),
                            TableColumn(key="source", label="来源"),
                            TableColumn(key="title", label="标题"),
                            TableColumn(key="time", label="时间"),
                            TableColumn(key="url", label="URL"),
                        ],
                        rows=[
                            {
                                "evidence_id": f"external:{index}",
                                "source": item.source_name,
                                "title": item.title,
                                "time": (
                                    item.data_time or item.retrieved_at
                                ).isoformat()
                                if (item.data_time or item.retrieved_at)
                                else None,
                                "url": item.url,
                            }
                            for index, item in enumerate(
                                narrative.external_evidence,
                                start=1,
                            )
                        ],
                    ),
                ),
            ]
        )

    for conflict in narrative.conflicts:
        blocks.append(
            CalloutBlock(
                type="callout",
                data=CalloutData(
                    title=f"证据冲突：{conflict.topic}",
                    text=(
                        f"内部观点：{conflict.internal_view}；"
                        f"外部观点：{conflict.external_view}；"
                        f"影响：{conflict.risk}"
                    ),
                    severity="warning",
                ),
            )
        )

    blocks.extend(
        [
            HeadingBlock(type="heading", data=HeadingData(text="六、数据与方法")),
            TableBlock(
                type="table",
                data=TableData(
                    columns=[
                        TableColumn(key="item", label="项目"),
                        TableColumn(key="value", label="说明"),
                    ],
                    rows=[
                        {
                            "item": "数据窗口",
                            "value": (
                                f"{analysis.data_window.start.isoformat()} 至 "
                                f"{analysis.data_window.end.isoformat()}"
                            ),
                        },
                        {
                            "item": "计算版本",
                            "value": analysis.calculation_version,
                        },
                        *[
                            {"item": f"方法 {index}", "value": method}
                            for index, method in enumerate(analysis.methods, start=1)
                        ],
                    ],
                ),
            ),
        ]
    )
    return ReportIR(blocks=blocks)


def _risk_block(signal: EnergyRiskSignal) -> CalloutBlock:
    return CalloutBlock(
        type="callout",
        data=CalloutData(
            title=signal.title,
            text=signal.detail,
            severity=signal.severity,
            evidence_ids=signal.evidence_record_ids,
        ),
    )


def _indicator_status(
    indicator_id: str,
    risks: list[EnergyRiskSignal],
) -> KpiStatus:
    severities = [
        signal.severity
        for signal in risks
        if signal.indicator_id == indicator_id
    ]
    if not severities:
        return "normal"
    severity = max(severities, key=_SEVERITY_ORDER.__getitem__)
    return "normal" if severity == "info" else severity


def _all_evidence_ids(analysis: EnergyMarketAnalysis) -> list[str]:
    return list(
        dict.fromkeys(
            record_id
            for item in analysis.indicators
            for record_id in item.evidence_record_ids
        )
    )


def _round_optional(value: float | None, *, digits: int = 2) -> float | None:
    return round(value, digits) if value is not None else None
