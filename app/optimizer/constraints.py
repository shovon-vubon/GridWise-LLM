from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class HourProfile:
    hour: int
    demand_kwh: float
    solar_kwh: float
    tariff_bdt_per_kwh: float


@dataclass
class BatterySpec:
    capacity_kwh: float
    initial_energy_kwh: float
    minimum_energy_kwh: float
    max_charge_kwh_per_hour: float
    max_discharge_kwh_per_hour: float


@dataclass
class DirectiveConstraintSet:
    solar_reduction_factor: Dict[int, float]
    minimum_battery_reserve: Dict[int, float]
    no_charge_hours: set[int]
    no_discharge_hours: set[int]
    max_grid_limit: Dict[int, float]


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_directive_constraints(directives: Optional[Iterable[Dict[str, Any]]], hours_count: int) -> DirectiveConstraintSet:
    solar_reduction_factor: Dict[int, float] = {hour: 0.0 for hour in range(hours_count)}
    minimum_battery_reserve: Dict[int, float] = {hour: 0.0 for hour in range(hours_count)}
    no_charge_hours: set[int] = set()
    no_discharge_hours: set[int] = set()
    max_grid_limit: Dict[int, float] = {hour: float("inf") for hour in range(hours_count)}

    if not directives:
        return DirectiveConstraintSet(
            solar_reduction_factor=solar_reduction_factor,
            minimum_battery_reserve=minimum_battery_reserve,
            no_charge_hours=no_charge_hours,
            no_discharge_hours=no_discharge_hours,
            max_grid_limit=max_grid_limit,
        )

    for directive in directives:
        if not isinstance(directive, dict):
            continue

        if directive.get("applies") is False:
            continue

        directive_type = directive.get("directive_type")
        adjustment = directive.get("structured_adjustment") or {}
        hours = adjustment.get("hours") or []

        if not isinstance(hours, list):
            continue

        for hour in hours:
            try:
                hour_index = int(hour)
            except (TypeError, ValueError):
                continue

            if 0 <= hour_index < hours_count:
                if directive_type == "solar_reduction":
                    factor = _coerce_float(adjustment.get("factor"), 0.0)
                    if factor < 0:
                        factor = 0.0
                    solar_reduction_factor[hour_index] = max(
                        solar_reduction_factor.get(hour_index, 0.0),
                        min(factor, 1.0),
                    )

                elif directive_type == "minimum_battery_reserve":
                    reserve = _coerce_float(adjustment.get("minimum_energy_kwh"), 0.0)
                    minimum_battery_reserve[hour_index] = max(
                        minimum_battery_reserve.get(hour_index, 0.0),
                        reserve,
                    )

                elif directive_type == "no_charge_window":
                    no_charge_hours.add(hour_index)

                elif directive_type == "no_discharge_window":
                    no_discharge_hours.add(hour_index)

                elif directive_type == "max_grid_window":
                    max_grid_value = _coerce_float(adjustment.get("max_grid_kwh"), float("inf"))
                    if max_grid_value >= 0:
                        max_grid_limit[hour_index] = min(
                            max_grid_limit.get(hour_index, float("inf")),
                            max_grid_value,
                        )

    return DirectiveConstraintSet(
        solar_reduction_factor=solar_reduction_factor,
        minimum_battery_reserve=minimum_battery_reserve,
        no_charge_hours=no_charge_hours,
        no_discharge_hours=no_discharge_hours,
        max_grid_limit=max_grid_limit,
    )
