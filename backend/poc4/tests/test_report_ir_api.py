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
            "title": title,
            "summary": "完整摘要",
            "key_findings": ["关键发现"],
            "risks": ["风险"],
            "suggestions": ["建议"],
            "data_window": {
                "start": "2026-06-05T00:00:00",
                "end": "2026-07-17T00:00:00",
                "description": "测试数据窗口",
            },
            "evidence": {"internal": [], "external": []},
            "conflicts": [],
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


def test_returns_latest_complete_report(api: tuple[TestClient, object]) -> None:
    client, engine = api
    with Session(engine) as session:
        older, _ = ReportRepository(session).save(_report("较早报告"))
        older.generated_at = datetime(2026, 8, 1, 8, 0, 0)
        newer, _ = ReportRepository(session).save(_report("最新报告"))
        newer.generated_at = datetime(2026, 8, 2, 8, 0, 0)
        session.commit()

    response = client.get("/api/ReportIR")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert "content-length" not in response.headers
    assert response.json() == _report("最新报告").model_dump(mode="json")
    assert "id" not in response.json()
    assert "content_sha256" not in response.json()


def test_returns_404_when_no_report_exists(api: tuple[TestClient, object]) -> None:
    client, _ = api

    response = client.get("/api/ReportIR")

    assert response.status_code == 404
    assert response.json() == {"detail": "ReportIR not found"}


def test_openapi_declares_report_ir_response() -> None:
    schema = app.openapi()
    response_schema = schema["paths"]["/api/ReportIR"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]

    assert response_schema["$ref"].endswith("/ReportIR")
