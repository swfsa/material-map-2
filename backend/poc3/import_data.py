import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from .database import get_session
from .models import MaterialRecord


DEFAULT_DATA_PATH = Path(__file__).with_name("data.json")

IMPORT_FIELDS = (
    "record_id",
    "category",
    "sub_category",
    "region",
    "metric_type",
    "value",
    "unit",
    "period",
    "source",
    "source_url",
    "confidence",
    "geo_scale",
    "mom_change",
    "yoy_change",
    "fetched_at",
    "raw_metadata",
    "geo_ref",
)

REQUIRED_SOURCE_FIELDS = {
    "id",
    "category",
    "sub_category",
    "metric_type",
    "value",
    "unit",
    "period",
    "source",
}


@dataclass(frozen=True)
class ImportStats:
    total: int
    inserted: int
    updated: int
    unchanged: int


def parse_datetime(value: Any, field_name: str, row_number: int) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"第 {row_number} 条的 {field_name} 必须是 ISO 日期字符串")

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"第 {row_number} 条的 {field_name} 不是有效 ISO 日期：{value!r}"
        ) from exc

    # MySQL DATETIME 不保存时区；统一转换为 UTC 后去掉 tzinfo。
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def map_source_record(source: dict[str, Any], row_number: int) -> dict[str, Any]:
    missing = sorted(REQUIRED_SOURCE_FIELDS - source.keys())
    if missing:
        raise ValueError(f"第 {row_number} 条缺少必填字段：{', '.join(missing)}")

    record_id = source["id"]
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError(f"第 {row_number} 条的 id 必须是非空字符串")

    for field_name in ("raw_metadata", "geo_ref"):
        value = source.get(field_name)
        if value is not None and not isinstance(value, dict):
            raise ValueError(f"第 {row_number} 条的 {field_name} 必须是对象或 null")

    raw_metadata = dict(source.get("raw_metadata") or {})
    if source.get("schema_version") is not None:
        raw_metadata["schema_version"] = source["schema_version"]

    mapped = {
        "record_id": record_id.strip(),
        "category": source.get("category"),
        "sub_category": source.get("sub_category"),
        "region": source.get("region"),
        "metric_type": source.get("metric_type"),
        "value": source.get("value"),
        "unit": source.get("unit"),
        "period": parse_datetime(source.get("period"), "period", row_number),
        "source": source.get("source"),
        "source_url": source.get("source_url"),
        "confidence": source.get("confidence"),
        "geo_scale": source.get("geo_scale"),
        "mom_change": source.get("mom_change"),
        "yoy_change": source.get("yoy_change"),
        "fetched_at": parse_datetime(source.get("fetched_at"), "fetched_at", row_number),
        "raw_metadata": raw_metadata or None,
        "geo_ref": dict(source["geo_ref"]) if source.get("geo_ref") else None,
    }

    # 通过 ORM 模型做最终字段类型校验，再转回待写入字典。
    validated = MaterialRecord.model_validate(mapped)
    return {field: getattr(validated, field) for field in IMPORT_FIELDS}


def load_records(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"找不到数据文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"JSON 格式错误：第 {exc.lineno} 行，第 {exc.colno} 列"
        ) from exc

    if not isinstance(payload, list):
        raise ValueError("data.json 顶层必须是数组")
    if not payload:
        raise ValueError("data.json 中没有可导入记录")

    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row_number, source in enumerate(payload, start=1):
        if not isinstance(source, dict):
            raise ValueError(f"第 {row_number} 条必须是 JSON 对象")
        record = map_source_record(source, row_number)
        record_id = record["record_id"]
        if record_id in seen_ids:
            raise ValueError(f"第 {row_number} 条出现重复 id：{record_id}")
        seen_ids.add(record_id)
        records.append(record)
    return records


def record_changed(existing: MaterialRecord, incoming: dict[str, Any]) -> bool:
    return any(getattr(existing, field) != incoming[field] for field in IMPORT_FIELDS)


def import_records(records: list[dict[str, Any]], dry_run: bool = False) -> ImportStats:
    record_ids = [record["record_id"] for record in records]

    with get_session() as session:
        try:
            existing_records = session.exec(
                select(MaterialRecord).where(MaterialRecord.record_id.in_(record_ids))
            ).all()
            existing_by_id = {
                record.record_id: record for record in existing_records
            }

            inserted = 0
            updated = 0
            unchanged = 0

            for incoming in records:
                existing = existing_by_id.get(incoming["record_id"])
                if existing is None:
                    inserted += 1
                    if not dry_run:
                        session.add(MaterialRecord(**incoming))
                elif record_changed(existing, incoming):
                    updated += 1
                    if not dry_run:
                        for field in IMPORT_FIELDS:
                            setattr(existing, field, incoming[field])
                        session.add(existing)
                else:
                    unchanged += 1

            if dry_run:
                session.rollback()
            else:
                session.commit()
        except Exception:
            session.rollback()
            raise

    return ImportStats(
        total=len(records),
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将 data.json 幂等导入 material_records 表"
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=f"JSON 文件路径（默认：{DEFAULT_DATA_PATH}）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只校验并统计，不写入数据库",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        records = load_records(args.path.resolve())
        stats = import_records(records, dry_run=args.dry_run)
    except (ValueError, SQLAlchemyError) as exc:
        raise SystemExit(f"导入失败：{exc}") from None

    mode = "预检" if args.dry_run else "导入"
    print(
        f"{mode}完成：总计 {stats.total}，新增 {stats.inserted}，"
        f"更新 {stats.updated}，未变化 {stats.unchanged}"
    )


if __name__ == "__main__":
    main()
