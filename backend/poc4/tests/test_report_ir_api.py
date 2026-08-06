from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from poc3.report import ReportIR
from poc3.repository import ReportRepository
from poc4.database import get_session
from poc4.main import app


def _report(title: str) -> ReportIR:
    return ReportIR.model_validate(
        {
            "blocks": [
                {
                    "type": "heading",
                    "data": {"text": title, "level": 1},
                },
                {
                    "type": "paragraph",
                    "data": {"text": "完整摘要", "evidence_ids": []},
                },
            ]
        }
    )


@pytest.fixture
def api() -> Iterator[tuple[TestClient, object]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_returns_latest_report_using_unified_contract(
    api: tuple[TestClient, object],
) -> None:
    client, engine = api
    with Session(engine) as session:
        older, _ = ReportRepository(session).save(_report("较早报告"))
        older.generated_at = datetime(2026, 8, 1, 8, 0, 0)
        newer, _ = ReportRepository(session).save(_report("最新报告"))
        newer.generated_at = datetime(2026, 8, 2, 8, 0, 0)
        session.commit()

    response = client.get("/api/reports/latest")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["report_ir"] == _report("最新报告").model_dump(mode="json")
    assert payload["generated_at"] == "2026-08-02T08:00:00Z"
    assert "<article" in payload["html"]
    assert "最新报告" in payload["html"]
    assert "id" not in payload
    assert "content_sha256" not in payload


def test_adapts_legacy_stored_report_to_blocks(api: tuple[TestClient, object]) -> None:
    client, engine = api
    legacy = {
        "title": "旧版报告",
        "summary": "旧版摘要",
        "key_findings": [],
        "risks": [],
        "suggestions": [],
        "data_window": {
            "start": "2026-07-01T00:00:00",
            "end": "2026-07-31T00:00:00",
            "description": "旧版窗口",
        },
        "evidence": {"internal": [], "external": []},
        "conflicts": [],
    }
    with Session(engine) as session:
        from poc3.models import ReportIRRecord

        session.add(
            ReportIRRecord(
                content_sha256="a" * 64,
                title="旧版报告",
                report_json=legacy,
                generated_at=datetime(2026, 8, 3, 8, 0, 0),
            )
        )
        session.commit()

    response = client.get("/api/reports/latest")

    assert response.status_code == 200
    assert response.json()["report_ir"]["blocks"][0]["data"]["text"] == "旧版报告"


def test_returns_404_when_no_report_exists(api: tuple[TestClient, object]) -> None:
    client, _ = api

    response = client.get("/api/reports/latest")

    assert response.status_code == 404
    assert response.json() == {"detail": "Report not found"}


def test_openapi_declares_latest_report_response() -> None:
    schema = app.openapi()
    response_schema = schema["paths"]["/api/reports/latest"]["get"]["responses"][
        "200"
    ]["content"]["application/json"]["schema"]

    assert response_schema["$ref"].endswith("/LatestReportResponse")
    assert "/api/ReportIR" not in schema["paths"]
