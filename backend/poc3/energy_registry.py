"""Internal EIA indicator registry used by analysis and Agent orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from .eia_import import SERIES_PROFILES


@dataclass(frozen=True)
class EnergyIndicatorProfile:
    indicator_id: str
    display_name: str
    series: str
    category: str
    sub_category: str
    region: str
    metric_type: str
    unit: str
    source_url: str


_INDICATOR_NAMES: dict[str, tuple[str, str]] = {
    "EMD_EPD2D_PTE_NUS_DPG": ("us_diesel_retail", "美国柴油零售价"),
    "EMM_EPM0_PTE_NUS_DPG": ("us_gasoline_retail", "美国汽油零售价"),
    "NW2_EPG0_SNO_R33_BCF": (
        "us_gas_storage_nonsalt_south_central",
        "美国中南部非盐穴天然气库存",
    ),
    "NW2_EPG0_SSO_R33_BCF": (
        "us_gas_storage_salt_south_central",
        "美国中南部盐穴天然气库存",
    ),
    "NW2_EPG0_SWO_R31_BCF": ("us_gas_storage_east", "美国东部天然气库存"),
    "NW2_EPG0_SWO_R32_BCF": (
        "us_gas_storage_midwest",
        "美国中西部天然气库存",
    ),
    "NW2_EPG0_SWO_R33_BCF": (
        "us_gas_storage_south_central",
        "美国中南部天然气库存",
    ),
    "NW2_EPG0_SWO_R34_BCF": (
        "us_gas_storage_mountain",
        "美国山区天然气库存",
    ),
    "NW2_EPG0_SWO_R35_BCF": (
        "us_gas_storage_pacific",
        "美国太平洋地区天然气库存",
    ),
    "NW2_EPG0_SWO_R48_BCF": (
        "us_gas_storage_lower48",
        "美国本土48州天然气库存",
    ),
    "RBRTE": ("brent_spot", "Brent 原油现货价"),
    "RNGWHHD": ("henry_hub_spot", "Henry Hub 天然气现货价"),
    "RWTC": ("wti_spot", "WTI 原油现货价"),
    "WCESTUS1": ("us_crude_oil_inventory", "美国原油库存"),
}


def _build_registry() -> dict[str, EnergyIndicatorProfile]:
    registry: dict[str, EnergyIndicatorProfile] = {}
    for series, source in SERIES_PROFILES.items():
        indicator_id, display_name = _INDICATOR_NAMES[series]
        registry[indicator_id] = EnergyIndicatorProfile(
            indicator_id=indicator_id,
            display_name=display_name,
            series=series,
            category=source.category,
            sub_category=source.sub_category,
            region=source.region,
            metric_type=source.metric_type,
            unit=source.unit,
            source_url=source.source_url,
        )
    return registry


ENERGY_INDICATORS = _build_registry()
DEFAULT_BRIEFING_INDICATORS: tuple[str, ...] = (
    "wti_spot",
    "brent_spot",
    "henry_hub_spot",
    "us_crude_oil_inventory",
)


def get_energy_indicator(indicator_id: str) -> EnergyIndicatorProfile:
    try:
        return ENERGY_INDICATORS[indicator_id]
    except KeyError as exc:
        supported = ", ".join(sorted(ENERGY_INDICATORS))
        raise ValueError(
            f"不支持的能源指标：{indicator_id!r}；当前支持：{supported}"
        ) from exc


def resolve_energy_indicators(
    indicator_ids: list[str] | tuple[str, ...],
) -> list[EnergyIndicatorProfile]:
    if not indicator_ids:
        raise ValueError("至少需要一个能源指标")
    if len(set(indicator_ids)) != len(indicator_ids):
        raise ValueError("能源指标不能重复")
    return [get_energy_indicator(indicator_id) for indicator_id in indicator_ids]
