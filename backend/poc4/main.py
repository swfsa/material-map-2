"""FastAPI entrypoint for material-record and ReportIR read APIs."""

from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from poc3.report import LatestReportResponse, ReportIR
from poc3.report_renderer import render_report_html
from poc3.response_models import MaterialIntelRecord
from poc3.streaming import stream_json_array
from poc4.database import get_session
from poc4.repository import get_latest_report, iter_material_records


app = FastAPI(
    title="EIA Energy Market Briefing API",
    version="0.2.0",
)

SessionDependency = Annotated[Session, Depends(get_session)]
STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


@app.get("/api/records", response_model=list[MaterialIntelRecord])
def get_records(
    session: SessionDependency,
    category: Annotated[str | None, Query(min_length=1)] = None,
    sub_category: Annotated[str | None, Query(min_length=1)] = None,
    source: Annotated[str | None, Query(min_length=1)] = None,
    period_from: date | None = None,
    period_to: date | None = None,
) -> StreamingResponse:
    """Stream filtered records as one backward-compatible JSON array."""
    if period_from is not None and period_to is not None and period_from > period_to:
        raise HTTPException(
            status_code=422,
            detail="period_from must be earlier than or equal to period_to",
        )

    rows = iter_material_records(
        session,
        category=category,
        sub_category=sub_category,
        source=source,
        period_from=period_from,
        period_to=period_to,
    )
    return StreamingResponse(
        stream_json_array(rows, to_model=MaterialIntelRecord.from_record),
        media_type="application/json",
        headers=STREAM_HEADERS,
    )


@app.get("/api/reports/latest", response_model=LatestReportResponse)
def get_latest_energy_report(
    session: SessionDependency,
) -> LatestReportResponse:
    """Return the latest validated report, deterministic HTML and DB timestamp."""

    stored = get_latest_report(session)
    if stored is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return LatestReportResponse(
        report_ir=stored.report_ir,
        html=render_report_html(stored.report_ir),
        generated_at=stored.generated_at,
    )


@app.get(
    "/api/ReportIR",
    response_model=ReportIR,
    deprecated=True,
    include_in_schema=False,
)
def get_legacy_report_ir(session: SessionDependency) -> ReportIR:
    """Temporary compatibility route; new clients use /api/reports/latest."""

    stored = get_latest_report(session)
    if stored is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return stored.report_ir
