import pytest
from pydantic import ValidationError

from poc3.report import ReportIR


def valid_report_payload() -> dict:
    return {
        "title": "Evidence report",
        "summary": "Internal and external evidence are separated.",
        "key_findings": ["Finding"],
        "risks": ["Conflicting signals may change the conclusion."],
        "suggestions": ["Monitor both sources."],
        "data_window": {
            "start": "2026-07-01T00:00:00",
            "end": "2026-07-29T00:00:00",
            "description": "Internal observations and external retrieval window.",
        },
        "evidence": {
            "internal": [
                {
                    "source_type": "internal",
                    "title": "Database record",
                    "source_name": "eia",
                    "summary": "Observed internal price.",
                    "data_time": "2026-07-17T00:00:00",
                }
            ],
            "external": [
                {
                    "source_type": "external",
                    "title": "Public report",
                    "source_name": "example.org",
                    "summary": "Public supply commentary.",
                    "url": "https://example.org/report",
                    "retrieved_at": "2026-07-29T00:00:00",
                }
            ],
        },
        "conflicts": [
            {
                "topic": "Supply direction",
                "internal_view": "Price increased.",
                "external_view": "Supply pressure may ease.",
                "risk": "Short-term direction remains uncertain.",
            }
        ],
    }


def test_preserves_evidence_time_groups_urls_and_conflicts() -> None:
    report = ReportIR.model_validate(valid_report_payload())

    assert len(report.evidence.internal) == 1
    assert len(report.evidence.external) == 1
    assert report.evidence.external[0].url == "https://example.org/report"
    assert report.data_window.start is not None
    assert len(report.conflicts) == 1
    assert "uncertain" in report.conflicts[0].risk


def test_rejects_external_evidence_without_url() -> None:
    payload = valid_report_payload()
    payload["evidence"]["external"][0]["url"] = None

    with pytest.raises(ValidationError, match="外部证据必须包含 URL"):
        ReportIR.model_validate(payload)
