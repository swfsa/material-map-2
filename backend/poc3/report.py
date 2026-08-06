"""Structured report contracts shared by Agent, persistence and HTTP APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Reject fields that are not part of the frozen public contract."""

    model_config = ConfigDict(extra="forbid")


EvidenceSourceType = Literal["internal", "external"]
RiskSeverity = Literal["info", "watch", "warning", "critical"]
TrendDirection = Literal["up", "down", "flat", "unknown"]
KpiStatus = Literal["normal", "watch", "warning", "critical"]
TableScalar = str | int | float | bool | None


class EvidenceItem(StrictModel):
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


class EvidenceGroups(StrictModel):
    internal: list[EvidenceItem] = Field(default_factory=list)
    external: list[EvidenceItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_groups(self) -> "EvidenceGroups":
        if any(item.source_type != "internal" for item in self.internal):
            raise ValueError("internal 分组只能包含内部证据")
        if any(item.source_type != "external" for item in self.external):
            raise ValueError("external 分组只能包含外部证据")
        return self


class DataWindow(StrictModel):
    start: datetime | None
    end: datetime | None
    description: str

    @model_validator(mode="after")
    def validate_order(self) -> "DataWindow":
        if self.start and self.end and self.start > self.end:
            raise ValueError("数据开始时间不能晚于结束时间")
        return self


class ConflictItem(StrictModel):
    topic: str
    internal_view: str
    external_view: str
    risk: str


class LegacyReportIR(StrictModel):
    """The pre-block report shape, retained only for stored-row migration."""

    title: str
    summary: str
    key_findings: list[str]
    risks: list[str]
    suggestions: list[str]
    data_window: DataWindow
    evidence: EvidenceGroups
    conflicts: list[ConflictItem] = Field(default_factory=list)


class HeadingData(StrictModel):
    text: str = Field(min_length=1)
    level: Literal[1, 2, 3] = 2


class ParagraphData(StrictModel):
    text: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)


class KpiItem(StrictModel):
    label: str = Field(min_length=1)
    value: str | float
    unit: str | None = None
    change: float | None = None
    change_period: str | None = None
    trend: TrendDirection = "unknown"
    status: KpiStatus = "normal"
    as_of: datetime | None = None
    source_record_ids: list[str] = Field(default_factory=list)


class KpiGridData(StrictModel):
    title: str | None = None
    items: list[KpiItem] = Field(min_length=1)


class CalloutData(StrictModel):
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    severity: RiskSeverity
    evidence_ids: list[str] = Field(default_factory=list)


class TableColumn(StrictModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    unit: str | None = None


class TableData(StrictModel):
    title: str | None = None
    columns: list[TableColumn] = Field(min_length=1)
    rows: list[dict[str, TableScalar]] = Field(default_factory=list)

    @model_validator(mode="after")
    def rows_only_use_declared_columns(self) -> "TableData":
        declared = {column.key for column in self.columns}
        if len(declared) != len(self.columns):
            raise ValueError("table columns 的 key 不能重复")
        for row in self.rows:
            unknown = set(row) - declared
            if unknown:
                names = ", ".join(sorted(unknown))
                raise ValueError(f"table row 包含未声明列：{names}")
        return self


class HeadingBlock(StrictModel):
    type: Literal["heading"]
    data: HeadingData


class ParagraphBlock(StrictModel):
    type: Literal["paragraph"]
    data: ParagraphData


class KpiGridBlock(StrictModel):
    type: Literal["kpiGrid"]
    data: KpiGridData


class CalloutBlock(StrictModel):
    type: Literal["callout"]
    data: CalloutData


class TableBlock(StrictModel):
    type: Literal["table"]
    data: TableData


ReportBlock = Annotated[
    HeadingBlock | ParagraphBlock | KpiGridBlock | CalloutBlock | TableBlock,
    Field(discriminator="type"),
]


class ReportIR(StrictModel):
    """Renderer-independent report intermediate representation."""

    blocks: list[ReportBlock] = Field(min_length=1)


class LatestReportResponse(StrictModel):
    report_ir: ReportIR
    html: str
    generated_at: datetime


class EnergyNarrative(StrictModel):
    """LLM-owned prose only; numerical blocks are assembled by Python code."""

    summary: str = Field(min_length=1)
    trend_commentary: str = Field(min_length=1)
    risk_commentary: str = Field(min_length=1)
    recommendations: list[str] = Field(default_factory=list)
    external_evidence: list[EvidenceItem] = Field(default_factory=list)
    conflicts: list[ConflictItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def only_external_evidence_is_allowed(self) -> "EnergyNarrative":
        if any(item.source_type != "external" for item in self.external_evidence):
            raise ValueError("EnergyNarrative.external_evidence 只能包含外部证据")
        return self


def report_title(report: ReportIR) -> str:
    """Return the first heading for database indexing."""

    for block in report.blocks:
        if isinstance(block, HeadingBlock):
            return block.data.text
    return "能源市场简报"


def legacy_report_to_blocks(legacy: LegacyReportIR) -> ReportIR:
    """Convert one stored v1 report to the unified block contract."""

    internal_ids = [
        f"legacy:internal:{index}"
        for index, _ in enumerate(legacy.evidence.internal, start=1)
    ]
    external_ids = [
        f"legacy:external:{index}"
        for index, _ in enumerate(legacy.evidence.external, start=1)
    ]
    all_evidence_ids = internal_ids + external_ids

    blocks: list[ReportBlock] = [
        HeadingBlock(type="heading", data=HeadingData(text=legacy.title, level=1)),
        ParagraphBlock(
            type="paragraph",
            data=ParagraphData(
                text=legacy.summary,
                evidence_ids=all_evidence_ids,
            ),
        ),
    ]

    if legacy.key_findings:
        blocks.append(
            HeadingBlock(type="heading", data=HeadingData(text="关键发现", level=2))
        )
        blocks.extend(
            ParagraphBlock(
                type="paragraph",
                data=ParagraphData(text=finding, evidence_ids=all_evidence_ids),
            )
            for finding in legacy.key_findings
        )

    if legacy.risks:
        blocks.append(
            HeadingBlock(type="heading", data=HeadingData(text="风险监测", level=2))
        )
        blocks.extend(
            CalloutBlock(
                type="callout",
                data=CalloutData(
                    title=f"风险 {index}",
                    text=risk,
                    severity="warning",
                    evidence_ids=all_evidence_ids,
                ),
            )
            for index, risk in enumerate(legacy.risks, start=1)
        )

    if legacy.suggestions:
        blocks.append(
            HeadingBlock(type="heading", data=HeadingData(text="建议", level=2))
        )
        blocks.append(
            TableBlock(
                type="table",
                data=TableData(
                    columns=[TableColumn(key="suggestion", label="建议")],
                    rows=[{"suggestion": item} for item in legacy.suggestions],
                ),
            )
        )

    evidence_rows: list[dict[str, TableScalar]] = []
    for evidence_id, item in zip(internal_ids, legacy.evidence.internal, strict=True):
        evidence_rows.append(_legacy_evidence_row(evidence_id, item))
    for evidence_id, item in zip(external_ids, legacy.evidence.external, strict=True):
        evidence_rows.append(_legacy_evidence_row(evidence_id, item))
    if evidence_rows:
        blocks.append(
            HeadingBlock(type="heading", data=HeadingData(text="证据", level=2))
        )
        blocks.append(
            TableBlock(
                type="table",
                data=TableData(
                    columns=[
                        TableColumn(key="evidence_id", label="证据ID"),
                        TableColumn(key="source_type", label="类型"),
                        TableColumn(key="source_name", label="来源"),
                        TableColumn(key="title", label="标题"),
                        TableColumn(key="time", label="时间"),
                        TableColumn(key="url", label="URL"),
                    ],
                    rows=evidence_rows,
                ),
            )
        )

    for conflict in legacy.conflicts:
        blocks.append(
            CalloutBlock(
                type="callout",
                data=CalloutData(
                    title=f"证据冲突：{conflict.topic}",
                    text=(
                        f"内部观点：{conflict.internal_view}；"
                        f"外部观点：{conflict.external_view}；"
                        f"影响：{conflict.risk}"
                    ),
                    severity="warning",
                    evidence_ids=all_evidence_ids,
                ),
            )
        )

    return ReportIR(blocks=blocks)


def _legacy_evidence_row(
    evidence_id: str,
    item: EvidenceItem,
) -> dict[str, TableScalar]:
    evidence_time = item.data_time or item.retrieved_at
    return {
        "evidence_id": evidence_id,
        "source_type": item.source_type,
        "source_name": item.source_name,
        "title": item.title,
        "time": evidence_time.isoformat() if evidence_time else None,
        "url": item.url,
    }


def validate_stored_report(payload: dict[str, object]) -> ReportIR:
    """Validate a block report or adapt one legacy database payload."""

    if "blocks" in payload:
        return ReportIR.model_validate(payload)
    return legacy_report_to_blocks(LegacyReportIR.model_validate(payload))
