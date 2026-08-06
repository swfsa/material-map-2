from poc3.energy_analysis import EnergyMarketAnalysis
from poc3.report import EnergyNarrative, KpiGridBlock, TableBlock
from poc3.report_builder import build_energy_report


def test_builder_uses_analysis_for_numeric_blocks_and_narrative_for_prose() -> None:
    analysis = EnergyMarketAnalysis.model_validate(
        {
            "data_window": {
                "start": "2026-01-01T00:00:00",
                "end": "2026-02-01T00:00:00",
            },
            "indicators": [
                {
                    "indicator_id": "wti_spot",
                    "display_name": "WTI 原油现货价",
                    "source_series": "RWTC",
                    "metric_type": "price",
                    "region": "US-OK-CUSHING",
                    "unit": "USD/barrel",
                    "inferred_frequency": "daily",
                    "observation_count": 30,
                    "period_start": "2026-01-01T00:00:00",
                    "period_end": "2026-02-01T00:00:00",
                    "latest_value": 80.77,
                    "previous_value": 79.5,
                    "change_7d_percent": 1.5,
                    "change_30d_percent": 4.2,
                    "moving_average_30d": 76.2,
                    "annualized_volatility_30d_percent": 31.5,
                    "z_score_30d": 1.1,
                    "historical_percentile": 90.0,
                    "max_drawdown_percent": -8.0,
                    "trend": "up",
                    "evidence_record_ids": ["record-latest", "record-baseline"],
                }
            ],
            "risks": [
                {
                    "code": "high_volatility",
                    "indicator_id": "wti_spot",
                    "title": "WTI波动率偏高",
                    "detail": "30日年化波动率为31.50%。",
                    "severity": "watch",
                    "evidence_record_ids": ["record-latest"],
                }
            ],
            "methods": ["确定性测试方法"],
        }
    )
    narrative = EnergyNarrative(
        summary="市场摘要由 Agent 提供。",
        trend_commentary="趋势解释由 Agent 提供。",
        risk_commentary="风险解释由 Agent 提供。",
        recommendations=["持续跟踪库存和价格。"],
    )

    report = build_energy_report(analysis, narrative)

    kpi = next(block for block in report.blocks if isinstance(block, KpiGridBlock))
    assert kpi.data.items[0].value == 80.77
    assert kpi.data.items[0].change == 4.2
    assert kpi.data.items[0].status == "watch"
    trend_table = next(
        block
        for block in report.blocks
        if isinstance(block, TableBlock) and block.data.title == "能源指标统计"
    )
    assert trend_table.data.rows[0]["volatility"] == 31.5
    assert report.blocks[1].data.text == "市场摘要由 Agent 提供。"
