"""API response contracts that are intentionally separate from table models."""

from datetime import datetime
from typing import Any

from pydantic import ConfigDict
from sqlmodel import SQLModel

from poc3.models import MaterialRecord


class MaterialIntelRecord(SQLModel):
    """Stable frontend-facing view of a material record.

    This is not a table model. Database-only fields such as ``id``, ``record_id``,
    ``fetched_at`` and ``raw_metadata`` are deliberately not part of the API
    contract.
    """

    model_config = ConfigDict(extra="forbid")#如果传入未声明字段，Pydantic 应拒绝，而不是悄悄忽略。

    category: str
    sub_category: str
    region: str
    metric_type: str
    value: float
    unit: str
    period: datetime
    confidence: str
    geo_scale: str
    geo_ref: dict[str, Any]
    source: str
    source_url: str
    mom_change: float | None = None
    yoy_change: float | None = None

    @classmethod
    def from_record(cls, record: MaterialRecord) -> "MaterialIntelRecord":
        """Map one ORM row to the public response without leaking table fields."""

        return cls(
            category=record.category,
            sub_category=record.sub_category,
            region=record.region,
            metric_type=record.metric_type,
            value=record.value,
            unit=record.unit,
            period=record.period,
            confidence=record.confidence,
            geo_scale=record.geo_scale,
            geo_ref=record.geo_ref,
            source=record.source,
            source_url=record.source_url,
            mom_change=record.mom_change,
            yoy_change=record.yoy_change,
        )
