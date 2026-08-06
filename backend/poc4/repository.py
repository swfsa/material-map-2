"""Read queries used by the records API."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, time

from sqlmodel import Session, select

from poc3.models import MaterialRecord, ReportIRRecord
from poc3.report import ReportIR, validate_stored_report


@dataclass(frozen=True)
class LatestStoredReport:
    report_ir: ReportIR
    generated_at: datetime


def list_material_records(
    session: Session,
    *,
    category: str | None = None,
    sub_category: str | None = None,
    source: str | None = None,
    period_from: date | None = None,
    period_to: date | None = None,
) -> list[MaterialRecord]:
    """Return matching rows in chronological order for non-streaming callers."""

    return list(
        iter_material_records(
            session,
            category=category,
            sub_category=sub_category,
            source=source,
            period_from=period_from,
            period_to=period_to,
        )
    )


def iter_material_records(
    session: Session,
    *,
    category: str | None = None,
    sub_category: str | None = None,
    source: str | None = None,
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
    if sub_category is not None:
        statement = statement.where(MaterialRecord.sub_category == sub_category)
    if source is not None:
        statement = statement.where(MaterialRecord.source == source)
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


def get_latest_report(session: Session) -> LatestStoredReport | None:
    """Read, validate and normalize the newest stored report row."""

    statement = select(ReportIRRecord).order_by(
        ReportIRRecord.generated_at.desc(),
        ReportIRRecord.id.desc(),
    )
    row = session.exec(statement).first()
    if row is None:
        return None
    generated_at = row.generated_at
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=UTC)
    else:
        generated_at = generated_at.astimezone(UTC)
    return LatestStoredReport(
        report_ir=validate_stored_report(row.report_json),
        generated_at=generated_at,
    )


def get_latest_report_ir(session: Session) -> ReportIR | None:
    """Compatibility helper for callers that only need the block IR."""

    stored = get_latest_report(session)
    return stored.report_ir if stored else None
