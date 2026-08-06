from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, select

import poc3.import_data as import_data_module
from poc3.domain import MATERIAL_CATEGORIES
from poc3.eia_import import (
    SERIES_PROFILES,
    import_all_eia_series,
    import_eia_series,
    iter_eia_batches,
    map_eia_row,
)
from poc3.import_data import ImportStats
from poc3.models import MaterialRecord


def _row(**overrides):
    row = {
        "id": 1,
        "series_id": "PET.RWTC.D",
        "period": date(2026, 7, 1),
        "value": Decimal("65.1200"),
        "units": "$/BBL",
        "duoarea": "YCUOK",
        "area_name": "NA",
        "product": "EPCWTI",
        "product_name": "WTI Crude Oil",
        "process": "PF4",
        "process_name": "Spot Price FOB",
        "series": "RWTC",
        "series_description": "Cushing, OK WTI Spot Price FOB",
    }
    row.update(overrides)
    return row


def _source_engine():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE eia_data (
                    id INTEGER PRIMARY KEY,
                    series_id TEXT NOT NULL,
                    period DATE NOT NULL,
                    value NUMERIC,
                    units TEXT,
                    duoarea TEXT,
                    area_name TEXT,
                    product TEXT,
                    product_name TEXT,
                    process TEXT,
                    process_name TEXT,
                    series TEXT,
                    series_description TEXT
                )
                """
            )
        )
        insert = text(
            """
            INSERT INTO eia_data VALUES
            (:id, :series_id, :period, :value, :units, :duoarea, :area_name,
             :product, :product_name, :process, :process_name, :series,
             :series_description)
            """
        )
        connection.execute(insert, _row(id=1, period="2026-07-01", value=65.12))
        connection.execute(insert, _row(id=2, period="2026-07-02", value=66.5))
        connection.execute(insert, _row(id=3, period="2026-07-03", value=None))
        connection.execute(
            insert,
            _row(id=4, series="RBRTE", period="2026-07-04", value=67.25),
        )
    return engine


def test_maps_wti_row_to_existing_material_contract() -> None:
    record = map_eia_row(_row())

    assert record["record_id"] == "6f24bd97-d1e0-595c-af13-813c97bed50b"
    assert record["category"] == "energy"
    assert record["sub_category"] == "crude_oil"
    assert record["region"] == "US-OK-CUSHING"
    assert record["value"] == 65.12
    assert record["unit"] == "USD/barrel"
    assert record["source"] == "eia"
    assert record["fetched_at"] is None
    assert record["raw_metadata"]["series_id"] == "PET.RWTC.D"
    assert record["raw_metadata"]["units"] == "$/BBL"


@pytest.mark.parametrize(
    ("series", "sub_category", "region", "metric_type", "unit"),
    [
        ("EMD_EPD2D_PTE_NUS_DPG", "diesel", "US", "price", "USD/gallon"),
        ("EMM_EPM0_PTE_NUS_DPG", "gasoline", "US", "price", "USD/gallon"),
        (
            "NW2_EPG0_SNO_R33_BCF",
            "natural_gas_storage_nonsalt",
            "US-SOUTH-CENTRAL",
            "volume",
            "billion_cubic_feet",
        ),
        (
            "NW2_EPG0_SSO_R33_BCF",
            "natural_gas_storage_salt",
            "US-SOUTH-CENTRAL",
            "volume",
            "billion_cubic_feet",
        ),
        (
            "NW2_EPG0_SWO_R31_BCF",
            "natural_gas_storage",
            "US-EAST",
            "volume",
            "billion_cubic_feet",
        ),
        (
            "NW2_EPG0_SWO_R32_BCF",
            "natural_gas_storage",
            "US-MIDWEST",
            "volume",
            "billion_cubic_feet",
        ),
        (
            "NW2_EPG0_SWO_R33_BCF",
            "natural_gas_storage",
            "US-SOUTH-CENTRAL",
            "volume",
            "billion_cubic_feet",
        ),
        (
            "NW2_EPG0_SWO_R34_BCF",
            "natural_gas_storage",
            "US-MOUNTAIN",
            "volume",
            "billion_cubic_feet",
        ),
        (
            "NW2_EPG0_SWO_R35_BCF",
            "natural_gas_storage",
            "US-PACIFIC",
            "volume",
            "billion_cubic_feet",
        ),
        (
            "NW2_EPG0_SWO_R48_BCF",
            "natural_gas_storage",
            "US-LOWER-48",
            "volume",
            "billion_cubic_feet",
        ),
        ("RBRTE", "crude_oil", "EUROPE", "price", "USD/barrel"),
        ("RNGWHHD", "natural_gas", "US-HENRY-HUB", "price", "USD/MMBtu"),
        ("RWTC", "crude_oil", "US-OK-CUSHING", "price", "USD/barrel"),
        ("WCESTUS1", "crude_oil", "US", "volume", "thousand_barrels"),
    ],
)
def test_maps_every_supported_series_to_standard_contract(
    series: str,
    sub_category: str,
    region: str,
    metric_type: str,
    unit: str,
) -> None:
    record = map_eia_row(_row(series=series))

    assert record["category"] == "energy"
    assert record["sub_category"] == sub_category
    assert record["region"] == region
    assert record["metric_type"] == metric_type
    assert record["unit"] == unit
    assert record["raw_metadata"]["series"] == series


def test_profiles_match_all_series_in_the_audited_dump() -> None:
    assert set(SERIES_PROFILES) == {
        "EMD_EPD2D_PTE_NUS_DPG",
        "EMM_EPM0_PTE_NUS_DPG",
        "NW2_EPG0_SNO_R33_BCF",
        "NW2_EPG0_SSO_R33_BCF",
        "NW2_EPG0_SWO_R31_BCF",
        "NW2_EPG0_SWO_R32_BCF",
        "NW2_EPG0_SWO_R33_BCF",
        "NW2_EPG0_SWO_R34_BCF",
        "NW2_EPG0_SWO_R35_BCF",
        "NW2_EPG0_SWO_R48_BCF",
        "RBRTE",
        "RNGWHHD",
        "RWTC",
        "WCESTUS1",
    }


def test_every_eia_sub_category_is_queryable_by_the_agent_repository() -> None:
    assert {
        profile.sub_category for profile in SERIES_PROFILES.values()
    } <= set(MATERIAL_CATEGORIES)


def test_rejects_unknown_series_and_null_value() -> None:
    with pytest.raises(ValueError, match="不支持的 EIA series"):
        map_eia_row(_row(series="UNKNOWN"))
    with pytest.raises(ValueError, match="value 为空"):
        map_eia_row(_row(value=None))


def test_reads_only_requested_series_in_batches_and_skips_null_values() -> None:
    engine = _source_engine()
    try:
        batches = list(iter_eia_batches(engine, batch_size=1))
    finally:
        engine.dispose()

    assert [[row["record_id"] for row in batch] for batch in batches] == [
        ["6f24bd97-d1e0-595c-af13-813c97bed50b"],
        ["df91834a-d372-54fd-941d-c8f66657137c"],
    ]


def test_import_aggregates_batch_stats_and_forwards_dry_run() -> None:
    engine = _source_engine()
    calls = []

    def fake_importer(records, dry_run):
        calls.append((records, dry_run))
        return ImportStats(len(records), len(records), 0, 0)

    try:
        stats = import_eia_series(
            engine,
            batch_size=1,
            dry_run=True,
            importer=fake_importer,
        )
    finally:
        engine.dispose()

    assert stats.source_rows == 2
    assert stats.inserted == 2
    assert len(calls) == 2
    assert all(dry_run is True for _, dry_run in calls)


def test_import_all_series_keeps_per_series_stats() -> None:
    engine = _source_engine()

    def fake_importer(records, dry_run):
        assert dry_run is True
        return ImportStats(len(records), len(records), 0, 0)

    try:
        stats_by_series = import_all_eia_series(
            engine,
            dry_run=True,
            importer=fake_importer,
        )
    finally:
        engine.dispose()

    assert set(stats_by_series) == set(SERIES_PROFILES)
    assert stats_by_series["RWTC"].source_rows == 2
    assert stats_by_series["RBRTE"].source_rows == 1
    assert sum(item.source_rows for item in stats_by_series.values()) == 3


def test_real_import_path_is_idempotent_with_sqlite_target(monkeypatch) -> None:
    source_engine = _source_engine()
    target_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(target_engine)

    def target_session():
        return Session(target_engine)

    monkeypatch.setattr(import_data_module, "get_session", target_session)
    try:
        first = import_eia_series(source_engine)
        second = import_eia_series(source_engine)
        with Session(target_engine) as session:
            rows = session.exec(select(MaterialRecord)).all()
    finally:
        source_engine.dispose()
        target_engine.dispose()

    assert (first.inserted, first.unchanged) == (2, 0)
    assert (second.inserted, second.unchanged) == (0, 2)
    assert [row.record_id for row in rows] == [
        "6f24bd97-d1e0-595c-af13-813c97bed50b",
        "df91834a-d372-54fd-941d-c8f66657137c",
    ]
