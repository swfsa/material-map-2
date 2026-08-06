from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from threading import Lock

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from poc3.models import MaterialRecord
from poc3.energy_registry import get_energy_indicator
from poc3.repository import (
    MaterialRepository,
    SessionPerQueryMaterialRepository,
)


@pytest.fixture
def sqlite_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                MaterialRecord(
                    record_id="oil-1",
                    sub_category="crude_oil",
                    region="US",
                    value=70.0,
                    period=datetime(2026, 1, 1),
                ),
                MaterialRecord(
                    record_id="oil-2",
                    sub_category="crude_oil",
                    region="US",
                    value=80.0,
                    period=datetime(2026, 2, 1),
                ),
                MaterialRecord(
                    record_id="oil-cn",
                    sub_category="crude_oil",
                    region="CN",
                    value=75.0,
                    period=datetime(2026, 1, 15),
                ),
                MaterialRecord(
                    record_id="food-1",
                    sub_category="food_price_index",
                    region="global",
                    value=120.0,
                    period=datetime(2026, 1, 1),
                ),
            ]
        )
        session.commit()

    yield engine
    engine.dispose()


def test_filters_date_region_orders_desc_and_limits(
    sqlite_engine: Engine,
) -> None:
    with Session(sqlite_engine) as session:
        records = MaterialRepository(session).query_material(
            "crude_oil",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 1),
            region="US",
            limit=1,
        )

    assert [record.record_id for record in records] == ["oil-2"]


def test_rejects_invalid_date_range(sqlite_engine: Engine) -> None:
    with Session(sqlite_engine) as session:
        repository = MaterialRepository(session)
        with pytest.raises(ValueError, match="start_date"):
            repository.query_material(
                "crude_oil",
                start_date=date(2026, 2, 1),
                end_date=date(2026, 1, 1),
            )


def test_rejects_invalid_limit(sqlite_engine: Engine) -> None:
    with Session(sqlite_engine) as session:
        repository = MaterialRepository(session)
        with pytest.raises(ValueError, match="limit"):
            repository.query_material("crude_oil", limit=0)


def test_energy_series_query_uses_exact_profile_and_has_no_agent_limit() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    profile = get_energy_indicator("wti_spot")
    with Session(engine) as session:
        session.add_all(
            [
                MaterialRecord(
                    record_id=f"wti-{index}",
                    category="energy",
                    sub_category="crude_oil",
                    region="US-OK-CUSHING",
                    metric_type="price",
                    value=70.0 + index,
                    unit="USD/barrel",
                    period=datetime(2026, 1, 1) + timedelta(days=index),
                    source="eia",
                    raw_metadata={"series": "RWTC"},
                )
                for index in range(120)
            ]
        )
        session.add(
            MaterialRecord(
                record_id="wrong-series",
                category="energy",
                sub_category="crude_oil",
                region="US-OK-CUSHING",
                metric_type="price",
                value=99.0,
                unit="USD/barrel",
                period=datetime(2026, 6, 1),
                source="eia",
                raw_metadata={"series": "NOT_RWTC"},
            )
        )
        session.commit()

        records = MaterialRepository(session).query_energy_series(profile)

    assert len(records) == 120
    assert records[0].record_id == "wti-0"
    assert records[-1].record_id == "wti-119"
    engine.dispose()


def test_session_per_query_repository_is_safe_for_concurrent_calls(
    tmp_path,
) -> None:
    database_path = (tmp_path / "concurrent.sqlite").as_posix()
    engine = create_engine(f"sqlite:///{database_path}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            MaterialRecord(
                record_id="oil-concurrent",
                sub_category="crude_oil",
                region="US",
                value=82.0,
                period=datetime(2026, 7, 29),
            )
        )
        session.commit()

    created_sessions: list[Session] = []
    closed_session_ids: list[int] = []
    tracking_lock = Lock()

    class TrackingSession(Session):
        def close(self) -> None:
            with tracking_lock:
                closed_session_ids.append(id(self))
            super().close()

    def session_factory() -> Session:
        session = TrackingSession(engine)
        with tracking_lock:
            # 保留强引用，避免快速测试中对象释放后 Python 复用 id。
            created_sessions.append(session)
        return session

    repository = SessionPerQueryMaterialRepository(session_factory)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(
                repository.query_material,
                "crude_oil",
                limit=1,
            )
            for _ in range(4)
        ]
        results = [future.result() for future in futures]

    assert [
        records[0].record_id
        for records in results
    ] == ["oil-concurrent"] * 4
    created_session_ids = [id(session) for session in created_sessions]
    assert len(created_sessions) == 4
    assert len(set(created_session_ids)) == 4
    assert sorted(closed_session_ids) == sorted(created_session_ids)
    engine.dispose()
