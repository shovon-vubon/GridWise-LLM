from __future__ import annotations

from typing import Any, Dict, List, Optional

from ortools.sat.python import cp_model

from app.optimizer.constraints import BatterySpec, DirectiveConstraintSet, HourProfile, build_directive_constraints


class EnergyOptimizer:
    def __init__(
        self,
        hourly_data: List[Dict[str, Any]],
        battery: Dict[str, Any],
        directives: Optional[List[Dict[str, Any]]] = None,
    ):
        self.hourly_data = [
            HourProfile(
                hour=int(hour["hour"]),
                demand_kwh=float(hour["demand_kwh"]),
                solar_kwh=float(hour["solar_kwh"]),
                tariff_bdt_per_kwh=float(hour["tariff_bdt_per_kwh"]),
            )
            for hour in hourly_data
        ]

        self.battery = BatterySpec(
            capacity_kwh=float(battery["capacity_kwh"]),
            initial_energy_kwh=float(battery["initial_energy_kwh"]),
            minimum_energy_kwh=float(battery["minimum_energy_kwh"]),
            max_charge_kwh_per_hour=float(battery["max_charge_kwh_per_hour"]),
            max_discharge_kwh_per_hour=float(battery["max_discharge_kwh_per_hour"]),
        )

        self.directives = directives or []
        self.constraint_set = build_directive_constraints(self.directives, len(self.hourly_data))

    def _scale(self, value: float) -> int:
        return int(round(value * 100.0))

    def solve(self) -> Dict[str, Any]:
        if not self.hourly_data:
            raise ValueError("At least one hourly record is required.")

        model = cp_model.CpModel()
        hours = len(self.hourly_data)

        scale = 100

        grid_import = [
            model.NewIntVar(0, self._scale(self._max_grid_limit_for_hour(hour)), f"grid_{hour}")
            for hour in range(hours)
        ]

        charge = [
            model.NewIntVar(
                0,
                self._scale(self.battery.max_charge_kwh_per_hour),
                f"charge_{hour}",
            )
            for hour in range(hours)
        ]

        discharge = [
            model.NewIntVar(
                0,
                self._scale(self.battery.max_discharge_kwh_per_hour),
                f"discharge_{hour}",
            )
            for hour in range(hours)
        ]

        battery_energy = [
            model.NewIntVar(
                self._scale(self.battery.minimum_energy_kwh),
                self._scale(self.battery.capacity_kwh),
                f"battery_{hour}",
            )
            for hour in range(hours)
        ]

        solar_used = [
            model.NewIntVar(0, self._scale(self.hourly_data[hour].solar_kwh), f"solar_used_{hour}")
            for hour in range(hours)
        ]

        model.Add(battery_energy[0] == self._scale(self.battery.initial_energy_kwh))

        for hour in range(hours):
            profile = self.hourly_data[hour]
            solar_limit = self._scale(max(0.0, profile.solar_kwh * (1.0 - self.constraint_set.solar_reduction_factor.get(hour, 0.0))))
            model.Add(solar_used[hour] <= solar_limit)

            if hour in self.constraint_set.no_charge_hours:
                model.Add(charge[hour] == 0)

            if hour in self.constraint_set.no_discharge_hours:
                model.Add(discharge[hour] == 0)

            reserve_target = self._scale(self.constraint_set.minimum_battery_reserve.get(hour, self.battery.minimum_energy_kwh))
            model.Add(battery_energy[hour] >= reserve_target)

            model.Add(grid_import[hour] <= self._scale(self._max_grid_limit_for_hour(hour)))

            if hour < hours - 1:
                model.Add(
                    battery_energy[hour + 1]
                    == battery_energy[hour] + charge[hour] - discharge[hour]
                )

            model.Add(
                grid_import[hour]
                + solar_used[hour]
                + discharge[hour]
                == self._scale(profile.demand_kwh)
                + charge[hour]
            )

        objective_terms = []
        for hour in range(hours):
            profile = self.hourly_data[hour]
            objective_terms.append(self._scale(profile.tariff_bdt_per_kwh) * grid_import[hour])

        model.Minimize(sum(objective_terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30
        solver.parameters.num_search_workers = 8
        status = solver.Solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise ValueError("No feasible schedule found for the provided scenario.")

        schedule = []
        total_cost = 0.0

        for hour in range(hours):
            profile = self.hourly_data[hour]
            grid_kwh = solver.Value(grid_import[hour]) / scale
            solar_kwh = solver.Value(solar_used[hour]) / scale
            charge_kwh = solver.Value(charge[hour]) / scale
            discharge_kwh = solver.Value(discharge[hour]) / scale
            energy_kwh = solver.Value(battery_energy[hour]) / scale
            total_cost += profile.tariff_bdt_per_kwh * grid_kwh

            schedule.append(
                {
                    "hour": profile.hour,
                    "demand_kwh": round(profile.demand_kwh, 2),
                    "solar_generation_kwh": round(profile.solar_kwh, 2),
                    "solar_used_kwh": round(solar_kwh, 2),
                    "grid_import_kwh": round(grid_kwh, 2),
                    "charge_kwh": round(charge_kwh, 2),
                    "discharge_kwh": round(discharge_kwh, 2),
                    "battery_energy_kwh": round(energy_kwh, 2),
                    "tariff_bdt_per_kwh": round(profile.tariff_bdt_per_kwh, 2),
                }
            )

        return {
            "status": "feasible",
            "objective_cost_bdt": round(total_cost, 2),
            "constraint_penalty_bdt": 0.0,
            "schedule": schedule,
        }

    def _max_grid_limit_for_hour(self, hour_index: int) -> float:
        limit = self.constraint_set.max_grid_limit.get(hour_index, float("inf"))
        if limit == float("inf"):
            return 1000000.0
        return float(limit)
