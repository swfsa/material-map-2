from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


EvidenceSourceType = Literal["internal", "external"]


class EvidenceItem(BaseModel):
    source_type: EvidenceSourceType
    title: str
    source_name: str
    summary: str
    url: str | None = None
    data_time: datetime | None = None
    retrieved_at: datetime | None = None

    @model_validator(mode="after")
    def external_evidence_requires_url(self) -> "EvidenceItem":
        if self.source_type == "external" and not self.url:
            raise ValueError("外部证据必须包含 URL")
        return self


class EvidenceGroups(BaseModel):
    internal: list[EvidenceItem] = Field(default_factory=list)
    external: list[EvidenceItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_groups(self) -> "EvidenceGroups":
        if any(item.source_type != "internal" for item in self.internal):
            raise ValueError("internal 分组只能包含内部证据")
        if any(item.source_type != "external" for item in self.external):
            raise ValueError("external 分组只能包含外部证据")
        return self


class DataWindow(BaseModel):
    start: datetime | None
    end: datetime | None
    description: str

    @model_validator(mode="after")
    def validate_order(self) -> "DataWindow":
        if self.start and self.end and self.start > self.end:
            raise ValueError("数据开始时间不能晚于结束时间")
        return self


class ConflictItem(BaseModel):
    topic: str
    internal_view: str
    external_view: str
    risk: str


class ReportIR(BaseModel):
    title: str
    summary: str
    key_findings: list[str]
    risks: list[str]
    suggestions: list[str]
    data_window: DataWindow
    evidence: EvidenceGroups
    conflicts: list[ConflictItem] = Field(default_factory=list)

