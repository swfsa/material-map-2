from poc3.report import ReportIR
from poc3.report_renderer import render_report_html


def test_renderer_escapes_text_and_renders_all_block_types() -> None:
    report = ReportIR.model_validate(
        {
            "blocks": [
                {
                    "type": "heading",
                    "data": {"text": "<script>alert(1)</script>", "level": 1},
                },
                {
                    "type": "paragraph",
                    "data": {"text": "A < B", "evidence_ids": ["record<1"]},
                },
                {
                    "type": "kpiGrid",
                    "data": {
                        "items": [
                            {
                                "label": "WTI",
                                "value": 80.77,
                                "unit": "USD/barrel",
                                "change": 1.25,
                                "change_period": "30d",
                                "trend": "up",
                            }
                        ]
                    },
                },
                {
                    "type": "callout",
                    "data": {
                        "title": "风险",
                        "text": "观察 & 核验",
                        "severity": "watch",
                    },
                },
                {
                    "type": "table",
                    "data": {
                        "columns": [{"key": "value", "label": "值"}],
                        "rows": [{"value": "<unsafe>"}],
                    },
                },
            ]
        }
    )

    rendered = render_report_html(report)

    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "A &lt; B" in rendered
    assert "record&lt;1" in rendered
    assert "观察 &amp; 核验" in rendered
    assert "&lt;unsafe&gt;" in rendered
    assert "report-kpi-grid" in rendered
    assert "report-callout watch" in rendered
