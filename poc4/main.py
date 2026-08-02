"""FastAPI entrypoint for material-record and ReportIR read APIs."""

from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from poc3.report import ReportIR
from poc3.response_models import MaterialIntelRecord
from poc3.streaming import stream_json_array, stream_json_object
from poc4.database import get_session
from poc4.repository import get_latest_report_ir, iter_material_records


app = FastAPI(
    title="Material Intelligence Read API",
    version="0.1.0",
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
        period_from=period_from,
        period_to=period_to,
    )
    return StreamingResponse(
        stream_json_array(rows, to_model=MaterialIntelRecord.from_record),
        media_type="application/json",
        headers=STREAM_HEADERS,
    )


@app.get("/api/ReportIR", response_model=ReportIR)
def get_report_ir(session: SessionDependency) -> StreamingResponse:
    """逐字段流式返回数据库中最近保存的一次完整 ReportIR。"""

    report = get_latest_report_ir(session)
    if report is None:
        raise HTTPException(status_code=404, detail="ReportIR not found")
    return StreamingResponse(
        stream_json_object(report),
        media_type="application/json",
        headers=STREAM_HEADERS,
    )
