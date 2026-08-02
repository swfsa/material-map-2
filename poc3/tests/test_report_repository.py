from datetime import datetime

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from poc3.report import ReportIR
from poc3.repository import ReportRepository, report_content_sha256


def _report(title: str = "测试报告") -> ReportIR:
    return ReportIR.model_validate(
        {
            "title": title,
            "summary": "摘要",
            "key_findings": ["发现"],
            "risks": ["风险"],
            "suggestions": ["建议"],
            "data_window": {
                "start": "2026-06-01T00:00:00",
                "end": "2026-07-01T00:00:00",
                "description": "测试窗口",
            },
            "evidence": {"internal": [], "external": []},
            "conflicts": [],
        }
    )


def test_save_report_is_idempotent() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    report = _report()

    try:
        with Session(engine) as session:
            first, first_created = ReportRepository(session).save(report)
            session.commit()
            second, second_created = ReportRepository(session).save(report)

            assert first_created is True
            assert second_created is False
            assert first.id == second.id
            assert first.content_sha256 == report_content_sha256(report)
            assert first.report_json["title"] == "测试报告"
            assert first.data_window_start == datetime(2026, 6, 1)
    finally:
        engine.dispose()
