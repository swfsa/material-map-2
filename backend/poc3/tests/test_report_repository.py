from datetime import datetime

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from poc3.report import ReportIR
from poc3.repository import ReportRepository, report_content_sha256


def _report(title: str = "测试报告") -> ReportIR:
    return ReportIR.model_validate(
        {
            "blocks": [
                {
                    "type": "heading",
                    "data": {"text": title, "level": 1},
                },
                {
                    "type": "paragraph",
                    "data": {"text": "摘要", "evidence_ids": []},
                },
            ]
        }
    )


def test_save_report_is_idempotent_and_indexes_derived_fields() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    report = _report()

    try:
        with Session(engine) as session:
            first, first_created = ReportRepository(session).save(
                report,
                data_window_start=datetime(2026, 6, 1),
                data_window_end=datetime(2026, 7, 1),
            )
            session.commit()
            second, second_created = ReportRepository(session).save(report)

            assert first_created is True
            assert second_created is False
            assert first.id == second.id
            assert first.content_sha256 == report_content_sha256(report)
            assert first.report_json["blocks"][0]["data"]["text"] == "测试报告"
            assert first.title == "测试报告"
            assert first.data_window_start == datetime(2026, 6, 1)
    finally:
        engine.dispose()
