"""Read queries used by the records API."""

from collections.abc import Iterator
from datetime import date, datetime, time

from sqlmodel import Session, select

from poc3.models import MaterialRecord, ReportIRRecord
from poc3.report import ReportIR


def list_material_records(
    session: Session,
    *,
    category: str | None = None,
    period_from: date | None = None,
    period_to: date | None = None,
) -> list[MaterialRecord]:
    """Return matching rows in chronological order for non-streaming callers."""

    return list(
        iter_material_records(
            session,
            category=category,
            period_from=period_from,
            period_to=period_to,
        )
    )


def iter_material_records(
    session: Session,
    *,
    category: str | None = None,
    period_from: date | None = None,
    period_to: date | None = None,
    batch_size: int = 100,
) -> Iterator[MaterialRecord]:
    """Execute the query once and let the response consume rows incrementally."""

    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero")

    statement = select(MaterialRecord)

    if category is not None:
        statement = statement.where(MaterialRecord.category == category)
    if period_from is not None:
        statement = statement.where(
            MaterialRecord.period >= datetime.combine(period_from, time.min)
        )
    if period_to is not None:
        statement = statement.where(
            MaterialRecord.period <= datetime.combine(period_to, time.max)
        )

    statement = statement.order_by(MaterialRecord.period.asc(), MaterialRecord.id.asc())
    result = session.exec(statement.execution_options(yield_per=batch_size))
    return iter(result)


def get_latest_report_ir(session: Session) -> ReportIR | None:
    """读取最近保存的一次 ReportIR，并重新执行响应合同校验。"""

    statement = select(ReportIRRecord).order_by(
        ReportIRRecord.generated_at.desc(),
        ReportIRRecord.id.desc(),
    )
    row = session.exec(statement).first()
    if row is None:
        return None
    return ReportIR.model_validate(row.report_json)
