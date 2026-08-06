import pytest
from pydantic import ValidationError

from poc3.report import (
    CalloutBlock,
    EnergyNarrative,
    LegacyReportIR,
    ReportIR,
    legacy_report_to_blocks,
    report_title,
    validate_stored_report,
)


def valid_block_payload() -> dict:
    return {
        "blocks": [
            {
                "type": "heading",
                "data": {"text": "EIA 能源市场简报", "level": 1},
            },
            {
                "type": "paragraph",
                "data": {"text": "市场摘要", "evidence_ids": ["record-1"]},
            },
            {
                "type": "kpiGrid",
                "data": {
                    "title": "市场状态",
                    "items": [
                        {
                            "label": "WTI 最新价",
                            "value": 80.77,
                            "unit": "USD/barrel",
                            "change": 2.5,
                            "change_period": "30d",
                            "trend": "up",
                            "status": "watch",
                            "source_record_ids": ["record-1"],
                        }
                    ],
                },
            },
            {
                "type": "callout",
                "data": {
                    "title": "波动风险",
                    "text": "波动率处于观察区间。",
                    "severity": "watch",
                    "evidence_ids": ["record-1"],
                },
            },
            {
                "type": "table",
                "data": {
                    "title": "趋势明细",
                    "columns": [
                        {"key": "indicator", "label": "指标"},
                        {"key": "value", "label": "最新值"},
                    ],
                    "rows": [{"indicator": "WTI", "value": 80.77}],
                },
            },
        ]
    }


def legacy_payload() -> dict:
    return {
        "title": "旧版报告",
        "summary": "旧版摘要",
        "key_findings": ["旧版发现"],
        "risks": ["旧版风险"],
        "suggestions": ["旧版建议"],
        "data_window": {
            "start": "2026-07-01T00:00:00",
            "end": "2026-07-29T00:00:00",
            "description": "旧版时间窗",
        },
        "evidence": {
            "internal": [
                {
                    "source_type": "internal",
                    "title": "数据库记录",
                    "source_name": "eia",
                    "summary": "内部价格数据",
                    "data_time": "2026-07-17T00:00:00",
                }
            ],
            "external": [
                {
                    "source_type": "external",
                    "title": "公开报告",
                    "source_name": "example.org",
                    "summary": "公开供应信息",
                    "url": "https://example.org/report",
                    "retrieved_at": "2026-07-29T00:00:00",
                }
            ],
        },
        "conflicts": [
            {
                "topic": "供应方向",
                "internal_view": "价格上涨",
                "external_view": "供应压力缓解",
                "risk": "短期方向不确定",
            }
        ],
    }


def test_validates_all_five_block_types() -> None:
    report = ReportIR.model_validate(valid_block_payload())

    assert [block.type for block in report.blocks] == [
        "heading",
        "paragraph",
        "kpiGrid",
        "callout",
        "table",
    ]
    assert report_title(report) == "EIA 能源市场简报"


def test_rejects_unknown_block_type_and_table_columns() -> None:
    payload = valid_block_payload()
    payload["blocks"][0]["type"] = "chart"
    with pytest.raises(ValidationError):
        ReportIR.model_validate(payload)

    payload = valid_block_payload()
    payload["blocks"][-1]["data"]["rows"][0]["unknown"] = "value"
    with pytest.raises(ValidationError, match="未声明列"):
        ReportIR.model_validate(payload)


def test_converts_legacy_report_and_preserves_evidence_and_conflicts() -> None:
    legacy = LegacyReportIR.model_validate(legacy_payload())
    report = legacy_report_to_blocks(legacy)

    assert report_title(report) == "旧版报告"
    assert any(
        isinstance(block, CalloutBlock) and block.data.title.startswith("证据冲突")
        for block in report.blocks
    )
    assert validate_stored_report(legacy_payload()) == report
    assert validate_stored_report(valid_block_payload()) == ReportIR.model_validate(
        valid_block_payload()
    )


def test_energy_narrative_rejects_internal_evidence() -> None:
    with pytest.raises(ValidationError, match="只能包含外部证据"):
        EnergyNarrative.model_validate(
            {
                "summary": "摘要",
                "trend_commentary": "趋势",
                "risk_commentary": "风险",
                "external_evidence": [
                    {
                        "source_type": "internal",
                        "title": "内部记录",
                        "source_name": "eia",
                        "summary": "内部数据",
                    }
                ],
            }
        )
