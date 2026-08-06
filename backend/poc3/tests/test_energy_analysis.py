from datetime import date, datetime, timedelta
import pytest

from poc3.energy_analysis import analyze_energy_market, analyze_energy_series
from poc3.energy_registry import get_energy_indicator
from poc3.models import MaterialRecord


def _records(values: list[float], *, unit: str = "USD/barrel") -> list[MaterialRecord]:
    start = datetime(2026, 1, 1)
    return [
        MaterialRecord(
            record_id=f"record-{index}",
            category="energy",
            sub_category="crude_oil",
            region="US-OK-CUSHING",
            metric_type="price",
            value=value,
            unit=unit,
            period=start + timedelta(days=index),
            source="eia",
        )
        for index, value in enumerate(values)
    ]


def test_calculates_state_trend_volatility_and_trace_ids() -> None:
    profile = get_energy_indicator("wti_spot")
    values = [70.0 + index * 0.2 for index in range(45)]

    analysis, risks = analyze_energy_series(profile, _records(values))

    assert analysis.observation_count == 45
    assert analysis.latest_value == pytest.approx(78.8)
    assert analysis.inferred_frequency == "daily"
    assert analysis.change_7d_percent is not None
    assert analysis.change_30d_percent is not None
    assert analysis.moving_average_30d is not None
    assert analysis.annualized_volatility_30d_percent is not None
    assert analysis.historical_percentile == 100.0
    assert analysis.trend == "up"
    assert analysis.evidence_record_ids[0] == "record-44"
    assert not any(signal.code == "no_data" for signal in risks)


def test_detects_statistical_anomaly_and_rejects_bad_series() -> None:
    profile = get_energy_indicator("wti_spot")
    _, risks = analyze_energy_series(profile, _records([100.0] * 29 + [200.0]))
    assert any(signal.code == "price_anomaly" for signal in risks)

    duplicate = _records([70.0, 71.0])
    duplicate[1].period = duplicate[0].period
    with pytest.raises(ValueError, match="重复 period"):
        analyze_energy_series(profile, duplicate)

    with pytest.raises(ValueError, match="单位不一致"):
        analyze_energy_series(profile, _records([70.0], unit="USD/MMBtu"))


def test_market_analysis_keeps_partial_data_and_reports_missing_indicator() -> None:
    class FakeRepository:
        def query_energy_series(self, indicator, **_kwargs):
            if indicator.indicator_id == "wti_spot":
                return _records([70.0, 71.0, 72.0])
            return []

    result = analyze_energy_market(
        FakeRepository(),
        ["wti_spot", "brent_spot"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert [item.indicator_id for item in result.indicators] == ["wti_spot"]
    assert any(signal.code == "no_data" for signal in result.risks)
    assert result.calculation_version == "energy-analysis/v1"
