"""
从独立恢复的 EIA staging 数据库导入指定 EIA 序列数据，并且不会执行 MySQL dump，也不会修改源数据库结构。
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from .import_data import ImportStats, import_records, map_source_record


@dataclass(frozen=True)
class EiaSeriesProfile:
    #定义一个 EIA 数据含义
    series: str
    category: str
    sub_category: str
    region: str
    metric_type: str
    unit: str
    source_url: str
    geo_scale: str
    geo_ref: dict[str, Any]


"""
配置支持哪些能源指标
    SELECT DISTINCT series  
    FROM eia_data
    WHERE series IS NOT NULL
    ORDER BY series;
目前一共14个能源指标

一个映射表：
    EIA编号
        |
        ↓
    业务含义
"""
SERIES_PROFILES: dict[str, EiaSeriesProfile] = {
    "EMD_EPD2D_PTE_NUS_DPG": EiaSeriesProfile(
        series="EMD_EPD2D_PTE_NUS_DPG",
        category="energy",
        sub_category="diesel",
        region="US",
        metric_type="price",
        unit="USD/gallon",
        source_url="https://www.eia.gov/opendata/",
        geo_scale="country",
        geo_ref={"country_code": "US"},
    ),
    "EMM_EPM0_PTE_NUS_DPG": EiaSeriesProfile(
        series="EMM_EPM0_PTE_NUS_DPG",
        category="energy",
        sub_category="gasoline",
        region="US",
        metric_type="price",
        unit="USD/gallon",
        source_url="https://www.eia.gov/opendata/",
        geo_scale="country",
        geo_ref={"country_code": "US"},
    ),
    "NW2_EPG0_SNO_R33_BCF": EiaSeriesProfile(
        series="NW2_EPG0_SNO_R33_BCF",
        category="energy",
        sub_category="natural_gas_storage_nonsalt",
        region="US-SOUTH-CENTRAL",
        metric_type="volume",
        unit="billion_cubic_feet",
        source_url="https://www.eia.gov/opendata/",
        geo_scale="country",
        geo_ref={"country_code": "US", "eia_storage_region": "R33"},
    ),
    "NW2_EPG0_SSO_R33_BCF": EiaSeriesProfile(
        series="NW2_EPG0_SSO_R33_BCF",
        category="energy",
        sub_category="natural_gas_storage_salt",
        region="US-SOUTH-CENTRAL",
        metric_type="volume",
        unit="billion_cubic_feet",
        source_url="https://www.eia.gov/opendata/",
        geo_scale="country",
        geo_ref={"country_code": "US", "eia_storage_region": "R33"},
    ),
    "NW2_EPG0_SWO_R31_BCF": EiaSeriesProfile(
        series="NW2_EPG0_SWO_R31_BCF",
        category="energy",
        sub_category="natural_gas_storage",
        region="US-EAST",
        metric_type="volume",
        unit="billion_cubic_feet",
        source_url="https://www.eia.gov/opendata/",
        geo_scale="country",
        geo_ref={"country_code": "US", "eia_storage_region": "R31"},
    ),
    "NW2_EPG0_SWO_R32_BCF": EiaSeriesProfile(
        series="NW2_EPG0_SWO_R32_BCF",
        category="energy",
        sub_category="natural_gas_storage",
        region="US-MIDWEST",
        metric_type="volume",
        unit="billion_cubic_feet",
        source_url="https://www.eia.gov/opendata/",
        geo_scale="country",
        geo_ref={"country_code": "US", "eia_storage_region": "R32"},
    ),
    "NW2_EPG0_SWO_R33_BCF": EiaSeriesProfile(
        series="NW2_EPG0_SWO_R33_BCF",
        category="energy",
        sub_category="natural_gas_storage",
        region="US-SOUTH-CENTRAL",
        metric_type="volume",
        unit="billion_cubic_feet",
        source_url="https://www.eia.gov/opendata/",
        geo_scale="country",
        geo_ref={"country_code": "US", "eia_storage_region": "R33"},
    ),
    "NW2_EPG0_SWO_R34_BCF": EiaSeriesProfile(
        series="NW2_EPG0_SWO_R34_BCF",
        category="energy",
        sub_category="natural_gas_storage",
        region="US-MOUNTAIN",
        metric_type="volume",
        unit="billion_cubic_feet",
        source_url="https://www.eia.gov/opendata/",
        geo_scale="country",
        geo_ref={"country_code": "US", "eia_storage_region": "R34"},
    ),
    "NW2_EPG0_SWO_R35_BCF": EiaSeriesProfile(
        series="NW2_EPG0_SWO_R35_BCF",
        category="energy",
        sub_category="natural_gas_storage",
        region="US-PACIFIC",
        metric_type="volume",
        unit="billion_cubic_feet",
        source_url="https://www.eia.gov/opendata/",
        geo_scale="country",
        geo_ref={"country_code": "US", "eia_storage_region": "R35"},
    ),
    "NW2_EPG0_SWO_R48_BCF": EiaSeriesProfile(
        series="NW2_EPG0_SWO_R48_BCF",
        category="energy",
        sub_category="natural_gas_storage",
        region="US-LOWER-48",
        metric_type="volume",
        unit="billion_cubic_feet",
        source_url="https://www.eia.gov/opendata/",
        geo_scale="country",
        geo_ref={"country_code": "US", "eia_storage_region": "R48"},
    ),
    "RBRTE": EiaSeriesProfile(
        series="RBRTE",
        category="energy",
        sub_category="crude_oil",
        region="EUROPE",
        metric_type="price",
        unit="USD/barrel",
        source_url="https://api.eia.gov/v2/petroleum/pri/spt/data/",
        geo_scale="country",
        geo_ref={"region_code": "EUROPE", "benchmark": "Brent"},
    ),
    "RNGWHHD": EiaSeriesProfile(
        series="RNGWHHD",
        category="energy",
        sub_category="natural_gas",
        region="US-HENRY-HUB",
        metric_type="price",
        unit="USD/MMBtu",
        source_url="https://www.eia.gov/opendata/",
        geo_scale="point",
        geo_ref={"country_code": "US", "place": "Henry Hub"},
    ),
    "RWTC": EiaSeriesProfile(
        series="RWTC",
        category="energy",
        sub_category="crude_oil",
        region="US-OK-CUSHING",
        metric_type="price",
        unit="USD/barrel",
        source_url="https://api.eia.gov/v2/petroleum/pri/spt/data/",
        geo_scale="city",
        geo_ref={"country_code": "US", "admin1_code": "OK", "place": "Cushing"},
    ),
    "WCESTUS1": EiaSeriesProfile(
        series="WCESTUS1",
        category="energy",
        sub_category="crude_oil",
        region="US",
        metric_type="volume",
        unit="thousand_barrels",
        source_url="https://www.eia.gov/opendata/",
        geo_scale="country",
        geo_ref={"country_code": "US"},
    ),
}
EIA_RECORD_NAMESPACE = UUID("a91dc597-ef6c-4fd9-8c82-5780524ed04f")


@dataclass(frozen=True)
class EiaImportStats:
    source_rows: int
    inserted: int
    updated: int
    unchanged: int


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def map_eia_row(row: Mapping[str, Any], row_number: int = 1) -> dict[str, Any]:
    """一条 EIA 数据 → 一条 MaterialRecord"""

    series = str(row.get("series") or "").strip()
    profile = SERIES_PROFILES.get(series)
    if profile is None:
        supported = ", ".join(sorted(SERIES_PROFILES))
        raise ValueError(f"不支持的 EIA series：{series!r}；当前支持：{supported}")

    period = row.get("period")
    if isinstance(period, (date, datetime)):
        period_text = period.isoformat()
    elif isinstance(period, str) and period.strip():
        period_text = period.strip()
    else:
        raise ValueError(f"第 {row_number} 条 EIA 记录缺少有效 period")

    value = row.get("value")
    if value is None:
        raise ValueError(f"第 {row_number} 条 EIA 记录的 value 为空")

    source = {
        "schema_version": "1.0",
        "id": str(
            uuid5(
                EIA_RECORD_NAMESPACE,
                f"eia|{profile.series}|{period_text[:10]}",
            )
        ),
        "category": profile.category,
        "sub_category": profile.sub_category,
        "region": profile.region,
        "metric_type": profile.metric_type,
        "value": float(value),
        "unit": profile.unit,
        "period": period_text,
        "source": "eia",
        "source_url": profile.source_url,
        "confidence": "official_periodic",
        "geo_scale": profile.geo_scale,
        "geo_ref": dict(profile.geo_ref),
        "mom_change": None,
        "yoy_change": None,
        # The dump does not contain the crawler retrieval time. Keeping this
        # null is more truthful than inventing a timestamp on every re-import.
        "fetched_at": None,
        "raw_metadata": {
            key: _json_value(row.get(key))
            for key in (
                "series_id",
                "series",
                "series_description",
                "units",
                "duoarea",
                "area_name",
                "product",
                "product_name",
                "process",
                "process_name",
            )
        },
    }
    return map_source_record(source, row_number)


def iter_eia_batches(
    engine: Engine,
    *,
    series: str = "RWTC",
    period_from: date | None = None,
    period_to: date | None = None,
    batch_size: int = 1000,
    limit: int | None = None,
) -> Iterator[list[dict[str, Any]]]:
    """分页读取数据库"""

    if series not in SERIES_PROFILES:
        raise ValueError(f"不支持的 EIA series：{series!r}")
    if batch_size < 1:
        raise ValueError("batch_size 必须大于 0")
    if limit is not None and limit < 1:
        raise ValueError("limit 必须大于 0")
    if period_from and period_to and period_from > period_to:
        raise ValueError("period_from 不能晚于 period_to")

    last_id = 0
    emitted = 0
    while limit is None or emitted < limit:
        current_size = batch_size if limit is None else min(batch_size, limit - emitted)
        conditions = ["series = :series", "id > :last_id", "value IS NOT NULL"]
        params: dict[str, Any] = {
            "series": series,
            "last_id": last_id,
            "batch_size": current_size,
        }
        if period_from is not None:
            conditions.append("period >= :period_from")
            params["period_from"] = period_from
        if period_to is not None:
            conditions.append("period <= :period_to")
            params["period_to"] = period_to

        statement = text(
            "SELECT id, series_id, period, value, units, duoarea, area_name, "
            "product, product_name, process, process_name, series, "
            "series_description FROM eia_data WHERE "
            + " AND ".join(conditions)
            + " ORDER BY id ASC LIMIT :batch_size"
        )
        with engine.connect() as connection:
            rows = connection.execute(statement, params).mappings().all()
        if not rows:
            break

        mapped = [
            map_eia_row(row, row_number=emitted + offset)
            for offset, row in enumerate(rows, start=1)
        ]
        yield mapped
        last_id = int(rows[-1]["id"])
        emitted += len(rows)


def import_eia_series(
    source_engine: Engine,
    *,
    series: str = "RWTC",
    period_from: date | None = None,
    period_to: date | None = None,
    batch_size: int = 1000,
    limit: int | None = None,
    dry_run: bool = False,
    importer: Callable[[list[dict[str, Any]], bool], ImportStats] = import_records,
) -> EiaImportStats:
    """执行单个指标导入"""

    total = inserted = updated = unchanged = 0
    for records in iter_eia_batches(
        source_engine,
        series=series,
        period_from=period_from,
        period_to=period_to,
        batch_size=batch_size,
        limit=limit,
    ):
        stats = importer(records, dry_run)
        total += stats.total
        inserted += stats.inserted
        updated += stats.updated
        unchanged += stats.unchanged
    return EiaImportStats(total, inserted, updated, unchanged)


def import_all_eia_series(
    source_engine: Engine,
    *,
    period_from: date | None = None,
    period_to: date | None = None,
    batch_size: int = 1000,
    limit: int | None = None,
    dry_run: bool = False,
    importer: Callable[[list[dict[str, Any]], bool], ImportStats] = import_records,
) -> dict[str, EiaImportStats]:
    """批量导入

    ``limit`` applies independently to each series, which makes
    ``--all-series --limit N --dry-run`` useful as a bounded mapping audit.
    """

    return {
        series: import_eia_series(
            source_engine,
            series=series,
            period_from=period_from,
            period_to=period_to,
            batch_size=batch_size,
            limit=limit,
            dry_run=dry_run,
            importer=importer,
        )
        for series in sorted(SERIES_PROFILES)
    }


def _date_arg(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("日期必须使用 YYYY-MM-DD") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从独立 EIA staging 数据库导入 EIA 数据到 material_records"
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--series", choices=sorted(SERIES_PROFILES))
    selection.add_argument(
        "--all-series",
        action="store_true",
        help="导入所有已配置 series；与 --series 互斥",
    )
    parser.add_argument("--period-from", type=_date_arg)
    parser.add_argument("--period-to", type=_date_arg)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_url = os.getenv("EIA_SOURCE_DATABASE_URL", "").strip()
    if not source_url:
        raise SystemExit(
            "未检测到 EIA_SOURCE_DATABASE_URL；请指向单独恢复的 EIA staging 数据库。"
        )

    source_engine = create_engine(source_url, pool_pre_ping=True)
    try:
        if args.all_series:
            stats_by_series = import_all_eia_series(
                source_engine,
                period_from=args.period_from,
                period_to=args.period_to,
                batch_size=args.batch_size,
                limit=args.limit,
                dry_run=args.dry_run,
            )
        else:
            selected_series = args.series or "RWTC"
            stats_by_series = {
                selected_series: import_eia_series(
                    source_engine,
                    series=selected_series,
                    period_from=args.period_from,
                    period_to=args.period_to,
                    batch_size=args.batch_size,
                    limit=args.limit,
                    dry_run=args.dry_run,
                )
            }
    except (ValueError, SQLAlchemyError) as exc:
        raise SystemExit(f"EIA 导入失败：{exc}") from None
    finally:
        source_engine.dispose()

    mode = "预检" if args.dry_run else "导入"
    for series, stats in stats_by_series.items():
        print(
            f"EIA {series} {mode}：源记录 {stats.source_rows}，"
            f"新增 {stats.inserted}，更新 {stats.updated}，"
            f"未变化 {stats.unchanged}"
        )

    total = EiaImportStats(
        source_rows=sum(stats.source_rows for stats in stats_by_series.values()),
        inserted=sum(stats.inserted for stats in stats_by_series.values()),
        updated=sum(stats.updated for stats in stats_by_series.values()),
        unchanged=sum(stats.unchanged for stats in stats_by_series.values()),
    )
    print(
        f"EIA {mode}合计：源记录 {total.source_rows}，新增 {total.inserted}，"
        f"更新 {total.updated}，未变化 {total.unchanged}"
    )


if __name__ == "__main__":
    main()
