"""Deterministic market state, trend, volatility and risk calculations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from math import sqrt
from statistics import fmean, median, pstdev, stdev
from typing import Protocol

from pydantic import Field, model_validator

from .energy_registry import EnergyIndicatorProfile, resolve_energy_indicators
from .models import MaterialRecord
from .report import RiskSeverity, StrictModel, TrendDirection


CALCULATION_VERSION = "energy-analysis/v1"


class EnergySeriesRepository(Protocol):
    def query_energy_series(
        self,
        indicator: EnergyIndicatorProfile,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MaterialRecord]: ...


class AnalysisDataWindow(StrictModel):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def validate_order(self) -> "AnalysisDataWindow":
        if self.start > self.end:
            raise ValueError("分析开始时间不能晚于结束时间")
        return self


class EnergyRiskSignal(StrictModel):
    code: str
    indicator_id: str
    title: str
    detail: str
    severity: RiskSeverity
    evidence_record_ids: list[str] = Field(default_factory=list)


class EnergyIndicatorAnalysis(StrictModel):
    indicator_id: str
    display_name: str
    source_series: str
    metric_type: str
    region: str
    unit: str
    inferred_frequency: str
    observation_count: int = Field(ge=1)
    period_start: datetime
    period_end: datetime
    latest_value: float
    previous_value: float | None = None
    change_7d_percent: float | None = None
    change_30d_percent: float | None = None
    moving_average_30d: float | None = None
    annualized_volatility_30d_percent: float | None = None
    z_score_30d: float | None = None
    historical_percentile: float
    max_drawdown_percent: float | None = None
    trend: TrendDirection
    evidence_record_ids: list[str] = Field(default_factory=list)


class EnergyMarketAnalysis(StrictModel):
    data_window: AnalysisDataWindow
    indicators: list[EnergyIndicatorAnalysis] = Field(min_length=1)
    risks: list[EnergyRiskSignal] = Field(default_factory=list)
    calculation_version: str = CALCULATION_VERSION
    methods: list[str] = Field(default_factory=list)


def analyze_energy_market(
    repository: EnergySeriesRepository,
    indicator_ids: list[str] | tuple[str, ...],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> EnergyMarketAnalysis:
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date 不能晚于 end_date")

    profiles = resolve_energy_indicators(indicator_ids)
    analyses: list[EnergyIndicatorAnalysis] = []
    risks: list[EnergyRiskSignal] = []
    for profile in profiles:
        records = repository.query_energy_series(
            profile,
            start_date=start_date,
            end_date=end_date,
        )
        if not records:
            risks.append(
                EnergyRiskSignal(
                    code="no_data",
                    indicator_id=profile.indicator_id,
                    title=f"{profile.display_name}无数据",
                    detail="请求时间窗内没有可用于分析的 EIA 记录。",
                    severity="warning",
                )
            )
            continue
        analysis, series_risks = analyze_energy_series(
            profile,
            records,
            requested_end=end_date,
        )
        analyses.append(analysis)
        risks.extend(series_risks)

    if not analyses:
        raise ValueError("请求的能源指标在给定时间窗内均无数据")

    window_start = min(item.period_start for item in analyses)
    window_end = max(item.period_end for item in analyses)
    return EnergyMarketAnalysis(
        data_window=AnalysisDataWindow(start=window_start, end=window_end),
        indicators=analyses,
        risks=risks,
        methods=[
            "7日和30日变化使用目标日前最近一个有效观测值作为基准",
            "30日波动率使用相邻观测简单收益率标准差并按推断频率年化",
            "趋势比较最新值与30日均值，偏离超过1%判定方向",
            "异常使用30日Z-score，回撤在请求时间窗内计算",
        ],
    )


def analyze_energy_series(
    profile: EnergyIndicatorProfile,
    records: Sequence[MaterialRecord],
    *,
    requested_end: date | None = None,
) -> tuple[EnergyIndicatorAnalysis, list[EnergyRiskSignal]]:
    points = _normalize_points(records, profile)
    latest = points[-1]
    previous = points[-2] if len(points) >= 2 else None
    baseline_7d = _baseline_at_or_before(points, latest.period - timedelta(days=7))
    baseline_30d = _baseline_at_or_before(points, latest.period - timedelta(days=30))
    recent = [point for point in points if point.period >= latest.period - timedelta(days=29)]
    recent_values = [point.value for point in recent]

    moving_average = fmean(recent_values) if recent_values else None
    frequency, annualization_factor, expected_gap_days = _infer_frequency(points)
    returns = [
        (current.value - prior.value) / abs(prior.value)
        for prior, current in zip(recent, recent[1:])
        if prior.value != 0
    ]
    volatility = (
        stdev(returns) * sqrt(annualization_factor) * 100
        if len(returns) >= 2
        else None
    )
    recent_std = pstdev(recent_values) if len(recent_values) >= 2 else 0.0
    z_score = (
        (latest.value - fmean(recent_values)) / recent_std
        if recent_std > 0
        else None
    )
    percentile = (
        sum(point.value <= latest.value for point in points) / len(points) * 100
    )
    drawdown = _max_drawdown_percent([point.value for point in points])
    trend = _trend(latest.value, moving_average)
    evidence_ids = _unique_ids(
        point.record_id
        for point in (latest, previous, baseline_7d, baseline_30d)
        if point is not None
    )

    analysis = EnergyIndicatorAnalysis(
        indicator_id=profile.indicator_id,
        display_name=profile.display_name,
        source_series=profile.series,
        metric_type=profile.metric_type,
        region=profile.region,
        unit=profile.unit,
        inferred_frequency=frequency,
        observation_count=len(points),
        period_start=points[0].period,
        period_end=latest.period,
        latest_value=latest.value,
        previous_value=previous.value if previous else None,
        change_7d_percent=_percent_change(latest.value, baseline_7d),
        change_30d_percent=_percent_change(latest.value, baseline_30d),
        moving_average_30d=moving_average,
        annualized_volatility_30d_percent=volatility,
        z_score_30d=z_score,
        historical_percentile=percentile,
        max_drawdown_percent=drawdown,
        trend=trend,
        evidence_record_ids=evidence_ids,
    )
    risks = _risk_signals(
        analysis,
        requested_end=requested_end,
        expected_gap_days=expected_gap_days,
    )
    return analysis, risks


class _Point:
    def __init__(self, record_id: str, period: datetime, value: float) -> None:
        self.record_id = record_id
        self.period = period
        self.value = value


def _normalize_points(
    records: Sequence[MaterialRecord],
    profile: EnergyIndicatorProfile,
) -> list[_Point]:
    points: list[_Point] = []
    seen_periods: set[datetime] = set()
    for record in sorted(records, key=lambda item: item.period or datetime.min):
        if record.period is None or record.value is None:
            continue
        if record.unit != profile.unit:
            raise ValueError(
                f"{profile.indicator_id} 存在单位不一致："
                f"期望 {profile.unit}，实际 {record.unit}"
            )
        if record.period in seen_periods:
            raise ValueError(
                f"{profile.indicator_id} 存在重复 period：{record.period.isoformat()}"
            )
        seen_periods.add(record.period)
        points.append(_Point(record.record_id, record.period, float(record.value)))
    if not points:
        raise ValueError(f"{profile.indicator_id} 没有有效 period/value")
    return points


def _baseline_at_or_before(points: Sequence[_Point], target: datetime) -> _Point | None:
    candidates = [point for point in points if point.period <= target]
    return candidates[-1] if candidates else None


def _percent_change(latest: float, baseline: _Point | None) -> float | None:
    if baseline is None or baseline.value == 0:
        return None
    return (latest - baseline.value) / abs(baseline.value) * 100


def _infer_frequency(points: Sequence[_Point]) -> tuple[str, int, int]:
    if len(points) < 2:
        return "unknown", 1, 30
    gaps = [
        max(1, (current.period.date() - prior.period.date()).days)
        for prior, current in zip(points, points[1:])
    ]
    typical_gap = median(gaps)
    if typical_gap <= 3:
        return "daily", 252, 3
    if typical_gap <= 10:
        return "weekly", 52, 10
    if typical_gap <= 40:
        return "monthly", 12, 40
    if typical_gap <= 100:
        return "quarterly", 4, 100
    return "annual", 1, 400


def _trend(latest: float, moving_average: float | None) -> TrendDirection:
    if moving_average is None or moving_average == 0:
        return "unknown"
    deviation = (latest - moving_average) / abs(moving_average)
    if deviation > 0.01:
        return "up"
    if deviation < -0.01:
        return "down"
    return "flat"


def _max_drawdown_percent(values: Sequence[float]) -> float | None:
    if not values:
        return None
    peak = values[0]
    max_drawdown = 0.0
    valid = False
    for value in values[1:]:
        if value > peak:
            peak = value
            continue
        if peak > 0:
            valid = True
            max_drawdown = min(max_drawdown, (value - peak) / peak * 100)
    return max_drawdown if valid else None


def _risk_signals(
    analysis: EnergyIndicatorAnalysis,
    *,
    requested_end: date | None,
    expected_gap_days: int,
) -> list[EnergyRiskSignal]:
    evidence = analysis.evidence_record_ids
    risks: list[EnergyRiskSignal] = []
    if analysis.observation_count < 3:
        risks.append(
            EnergyRiskSignal(
                code="insufficient_observations",
                indicator_id=analysis.indicator_id,
                title=f"{analysis.display_name}样本不足",
                detail="有效观测少于3条，趋势和波动结论不稳定。",
                severity="watch",
                evidence_record_ids=evidence,
            )
        )
    if analysis.z_score_30d is not None and abs(analysis.z_score_30d) >= 2:
        risks.append(
            EnergyRiskSignal(
                code="price_anomaly",
                indicator_id=analysis.indicator_id,
                title=f"{analysis.display_name}出现统计异常",
                detail=f"最新值的30日Z-score为 {analysis.z_score_30d:.2f}。",
                severity="warning",
                evidence_record_ids=evidence,
            )
        )
    if (
        analysis.metric_type == "price"
        and analysis.annualized_volatility_30d_percent is not None
        and analysis.annualized_volatility_30d_percent >= 30
    ):
        severity: RiskSeverity = (
            "warning"
            if analysis.annualized_volatility_30d_percent >= 60
            else "watch"
        )
        risks.append(
            EnergyRiskSignal(
                code="high_volatility",
                indicator_id=analysis.indicator_id,
                title=f"{analysis.display_name}波动率偏高",
                detail=(
                    "30日年化波动率为 "
                    f"{analysis.annualized_volatility_30d_percent:.2f}%。"
                ),
                severity=severity,
                evidence_record_ids=evidence,
            )
        )
    if (
        analysis.metric_type == "price"
        and analysis.max_drawdown_percent is not None
        and analysis.max_drawdown_percent <= -15
    ):
        risks.append(
            EnergyRiskSignal(
                code="large_drawdown",
                indicator_id=analysis.indicator_id,
                title=f"{analysis.display_name}存在较大回撤",
                detail=f"分析窗口最大回撤为 {analysis.max_drawdown_percent:.2f}%。",
                severity="warning",
                evidence_record_ids=evidence,
            )
        )
    if requested_end is not None:
        stale_days = (requested_end - analysis.period_end.date()).days
        if stale_days > expected_gap_days * 2:
            risks.append(
                EnergyRiskSignal(
                    code="stale_data",
                    indicator_id=analysis.indicator_id,
                    title=f"{analysis.display_name}数据可能过期",
                    detail=(
                        f"最新观测距请求截止日 {stale_days} 天，"
                        f"超过推断发布间隔的两倍。"
                    ),
                    severity="watch",
                    evidence_record_ids=evidence,
                )
            )
    return risks


def _unique_ids(values) -> list[str]:
    return list(dict.fromkeys(values))
