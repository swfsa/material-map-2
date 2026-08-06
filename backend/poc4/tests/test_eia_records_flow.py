from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session

import poc3.import_data as import_data_module
from poc3.eia_import import import_eia_series
from poc4.database import get_session
from poc4.main import app


def test_eia_staging_to_records_api_flow(monkeypatch) -> None:
    source_engine = create_engine("sqlite://")
    with source_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE eia_data (
                    id INTEGER PRIMARY KEY, series_id TEXT, period DATE,
                    value NUMERIC, units TEXT, duoarea TEXT, area_name TEXT,
                    product TEXT, product_name TEXT, process TEXT,
                    process_name TEXT, series TEXT, series_description TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO eia_data VALUES
                (1, 'PET.RWTC.D', '2026-07-01', 65.12, '$/BBL', 'YCUOK',
                 'NA', 'EPCWTI', 'WTI Crude Oil', 'PF4', 'Spot Price FOB',
                 'RWTC', 'Cushing, OK WTI Spot Price FOB')
                """
            )
        )

    target_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(target_engine)

    def target_session() -> Session:
        return Session(target_engine)

    def api_session() -> Iterator[Session]:
        with Session(target_engine) as session:
            yield session

    monkeypatch.setattr(import_data_module, "get_session", target_session)
    app.dependency_overrides[get_session] = api_session
    try:
        stats = import_eia_series(source_engine)
        with TestClient(app) as client:
            response = client.get(
                "/api/records",
                params={
                    "category": "energy",
                    "sub_category": "crude_oil",
                    "source": "eia",
                },
            )
    finally:
        app.dependency_overrides.clear()
        source_engine.dispose()
        target_engine.dispose()

    assert stats.inserted == 1
    assert response.status_code == 200
    assert all("series" not in item for item in response.json())
    assert response.json() == [
        {
            "category": "energy",
            "sub_category": "crude_oil",
            "region": "US-OK-CUSHING",
            "metric_type": "price",
            "value": 65.12,
            "unit": "USD/barrel",
            "period": "2026-07-01T00:00:00",
            "confidence": "official_periodic",
            "geo_scale": "city",
            "geo_ref": {
                "country_code": "US",
                "admin1_code": "OK",
                "place": "Cushing",
            },
            "source": "eia",
            "source_url": "https://api.eia.gov/v2/petroleum/pri/spt/data/",
            "mom_change": None,
            "yoy_change": None,
        }
    ]
