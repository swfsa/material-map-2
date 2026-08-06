from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from poc4.database import get_session
from poc4.main import app
from poc3.models import MaterialRecord


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(
            [
                _record("energy-2", "energy", datetime(2026, 1, 2), 82.0),
                _record("weather-1", "weather", datetime(2026, 1, 1), 18.5),
                _record(
                    "energy-1",
                    "energy",
                    datetime(2026, 1, 1),
                    80.0,
                    sub_category="crude_oil",
                    source="eia",
                ),
            ]
        )
        session.commit()

    def override_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def _record(
    record_id: str,
    category: str,
    period: datetime,
    value: float,
    *,
    sub_category: str | None = None,
    source: str = "test-source",
) -> MaterialRecord:
    return MaterialRecord(
        record_id=record_id,
        category=category,
        sub_category=sub_category or f"{category}_series",
        region="test-region",
        metric_type="price",
        value=value,
        unit="test-unit",
        period=period,
        confidence="official_periodic",
        geo_scale="global",
        geo_ref={"scope": "test"},
        source=source,
        source_url="https://example.test/data",
        mom_change=None,
        yoy_change=None,
    )


def test_filters_category_and_inclusive_period(client: TestClient) -> None:
    response = client.get(
        "/api/records",
        params={
            "category": "energy",
            "period_from": "2026-01-02",
            "period_to": "2026-01-02",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert "content-length" not in response.headers
    assert response.json() == [
        {
            "category": "energy",
            "sub_category": "energy_series",
            "region": "test-region",
            "metric_type": "price",
            "value": 82.0,
            "unit": "test-unit",
            "period": "2026-01-02T00:00:00",
            "confidence": "official_periodic",
            "geo_scale": "global",
            "geo_ref": {"scope": "test"},
            "source": "test-source",
            "source_url": "https://example.test/data",
            "mom_change": None,
            "yoy_change": None,
        }
    ]


def test_returns_only_public_fields_in_chronological_order(client: TestClient) -> None:
    response = client.get("/api/records", params={"category": "energy"})

    assert response.status_code == 200
    body = response.json()
    assert [item["period"] for item in body] == [
        "2026-01-01T00:00:00",
        "2026-01-02T00:00:00",
    ]
    assert set(body[0]) == {
        "category",
        "sub_category",
        "region",
        "metric_type",
        "value",
        "unit",
        "period",
        "confidence",
        "geo_scale",
        "geo_ref",
        "source",
        "source_url",
        "mom_change",
        "yoy_change",
    }


def test_filters_specific_eia_sub_category_and_source(client: TestClient) -> None:
    response = client.get(
        "/api/records",
        params={
            "category": "energy",
            "sub_category": "crude_oil",
            "source": "eia",
        },
    )

    assert response.status_code == 200
    assert [(item["sub_category"], item["source"]) for item in response.json()] == [
        ("crude_oil", "eia")
    ]


def test_rejects_reversed_period_range(client: TestClient) -> None:
    response = client.get(
        "/api/records",
        params={"period_from": "2026-01-03", "period_to": "2026-01-01"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "period_from must be earlier than or equal to period_to"
    )


def test_openapi_declares_material_record_array() -> None:
    schema = app.openapi()
    response_schema = schema["paths"]["/api/records"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]

    assert response_schema["type"] == "array"
    assert response_schema["items"]["$ref"].endswith("/MaterialIntelRecord")
