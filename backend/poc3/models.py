from datetime import UTC, datetime
from typing import Optional, Any

from sqlalchemy import JSON
from sqlmodel import (
    SQLModel,
    Field
)



class MaterialRecord(SQLModel, table=True):

    __tablename__ = "material_records"


    id: Optional[int] = Field(
        default=None,
        primary_key=True
    )


    record_id: str = Field(
        index=True,
        unique=True
    )


    category: Optional[str]=None


    sub_category: Optional[str]=Field(
        default=None,
        index=True
    )


    region: Optional[str]=None


    metric_type: Optional[str]=None


    value: Optional[float]=None


    unit: Optional[str]=None


    period: Optional[datetime]=Field(
        default=None,
        index=True
    )


    source: Optional[str]=None


    source_url: Optional[str]=None


    confidence: Optional[str]=None


    geo_scale: Optional[str]=None


    mom_change: Optional[float]=None


    yoy_change: Optional[float]=None


    fetched_at: Optional[datetime]=None


    raw_metadata: Optional[dict[str,Any]]=Field(
        default=None,
        sa_type=JSON
    )


    geo_ref: Optional[dict[str,Any]]=Field(
        default=None,
        sa_type=JSON
    )


class ReportIRRecord(SQLModel, table=True):
    """持久化 ReportIR 的数据库实体，不直接作为 API 响应模型。"""

    __tablename__ = "report_ir"

    id: int | None = Field(default=None, primary_key=True)
    content_sha256: str = Field(max_length=64, unique=True, index=True)
    title: str = Field(max_length=500, index=True)
    data_window_start: datetime | None = Field(default=None, index=True)
    data_window_end: datetime | None = Field(default=None, index=True)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None),
        index=True,
    )
    report_json: dict[str, Any] = Field(sa_type=JSON)
