"""Microscopic simulator of a one-lane freeway with one on-ramp merge.

Units: seconds, metres, metres/second, metres/second^2.
Every driver follows the Intelligent Driver Model (IDM). A connected and automated vehicle (CAV) uses the
shorter CAV time gap when the vehicle ahead is also a CAV, because it then receives that vehicle's state over
vehicle-to-vehicle (V2V) communication (cooperative adaptive cruise control, CACC). Behind a human driver it
keeps the human time gap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import deque
from typing import Any
import math
import random

import numpy as np
import pandas as pd


@dataclass
class Vehicle:
    vehicle_id: str
    x: float
    v: float
    a: float
    source: str            # "mainline", "ramp" or "virtual" (the zipper slot)
    cav: bool
    entry_time: float      # scheduled arrival time at the boundary
    spawn_time_s: float = 0.0
    accumulated_delay_s: float = 0.0
    min_gap_m: float = math.inf


@dataclass
class DetectorAccumulator:
    sensor_id: str
    position_m: float
    interval_s: float
    zone_length_m: float = 50.0
    interval_start_s: float = 0.0
    crossing_speeds: list[float] = field(default_factory=list)
    crossing_ids: list[str] = field(default_factory=list)
    occupancy_sum_pct_s: float = 0.0

    def sample_occupancy(self, vehicles: list[Vehicle], vehicle_length_m: float, dt: float) -> None:
        half = self.zone_length_m / 2.0
        n = sum(abs(v.x - self.position_m) <= half for v in vehicles)
        occupancy = min(100.0, 100.0 * n * vehicle_length_m / self.zone_length_m)
        self.occupancy_sum_pct_s += occupancy * dt

    def crossing(self, vehicle_id: str, speed_mps: float) -> None:
        self.crossing_ids.append(vehicle_id)
        self.crossing_speeds.append(speed_mps)

    def close_interval(self, end_s: float) -> dict[str, Any]:
        duration = max(end_s - self.interval_start_s, 1e-9)
        row = {
            "sensor_id": self.sensor_id,
            "interval_start_s": round(self.interval_start_s, 3),
            "interval_end_s": round(end_s, 3),
            "count": len(self.crossing_speeds),
            "mean_speed_mps": (
                float(np.mean(self.crossing_speeds)) if self.crossing_speeds else np.nan
            ),
            "occupancy_pct": self.occupancy_sum_pct_s / duration,
        }
        self.interval_start_s = end_s
        self.crossing_speeds.clear()
        self.crossing_ids.clear()
        self.occupancy_sum_pct_s = 0.0
        return row


class RampMeter:
    """Ramp-release controller: unmetered, fixed rate, or ALINEA-like occupancy feedback."""

    def __init__(self, cfg: dict[str, Any], update_s: float):
        self.cfg = cfg
        self.update_s = update_s
        self.mode = cfg["mode"]
        self.rate_vph = float(cfg["initial_rate_vph"])
        self.next_update_s = 0.0
        self.next_release_s = 0.0

    def update(self, time_s: float, observation: dict[str, Any] | None, queue_estimate: int) -> dict[str, Any] | None:
        if time_s + 1e-9 < self.next_update_s:
            return None
        self.next_update_s = time_s + self.update_s
        if self.mode == "unmetered":
            self.rate_vph = 1800.0
            reason = "unmetered"
        elif self.mode == "fixed" or observation is None or not np.isfinite(observation.get("occupancy_pct", np.nan)):
            self.rate_vph = float(self.cfg["fixed_rate_vph"])
            reason = "fixed rate" if self.mode == "fixed" else "no observation: fixed-rate fallback"
        else:
            error = float(self.cfg["target_occupancy_pct"]) - float(observation["occupancy_pct"])
            self.rate_vph += float(self.cfg["alinea_gain_vph_per_pct"]) * error
            reason = "ALINEA occupancy feedback"
            if queue_estimate >= int(self.cfg["queue_override_vehicles"]):
                self.rate_vph = float(self.cfg["maximum_rate_vph"])
                reason = "ramp storage override"
        self.rate_vph = float(np.clip(self.rate_vph, self.cfg["minimum_rate_vph"], self.cfg["maximum_rate_vph"]))
        return {"time_s": round(time_s, 3), "rate_vph": self.rate_vph, "reason": reason,
                "ramp_queue_veh": int(queue_estimate)}

    def release_due(self, time_s: float) -> bool:
        if self.mode == "unmetered":
            return True  # no meter: the front ramp vehicle may try to merge at every step
        if time_s + 1e-9 < self.next_release_s:
            return False
        interval = 3600.0 / max(self.rate_vph, 1.0)
        self.next_release_s = max(time_s, self.next_release_s) + interval
        return True


def idm_acceleration(
    vehicle: Vehicle,
    leader: Vehicle | None,
    desired_speed_mps: float,
    cfg: dict[str, float],
    vehicle_length_m: float,
) -> float:
    """Treiber-Hennecke-Helbing IDM with s1=0."""
    a = float(cfg["maximum_accel_mps2"])
    free_term = 1.0 - (vehicle.v / max(desired_speed_mps, 0.1)) ** float(cfg["accel_exponent"])
    if leader is None:
        return a * free_term
    gap = max(leader.x - vehicle.x - vehicle_length_m, 0.1)
    closing = vehicle.v - leader.v
    s_star = float(cfg["minimum_gap_m"]) + max(
        0.0,
        vehicle.v * float(cfg["desired_time_gap_s"])
        + vehicle.v * closing / (2.0 * math.sqrt(a * float(cfg["comfortable_decel_mps2"]))),
    )
    return a * (free_term - (s_star / gap) ** 2)


class FreewaySimulation:
    def __init__(
        self,
        sim_cfg: dict[str, Any],
        human_cfg: dict[str, Any],
        cav_cfg: dict[str, Any],
        meter_cfg: dict[str, Any],
        scenario: dict[str, Any],
    ):
        self.cfg = dict(sim_cfg)
        self.human_cfg = dict(human_cfg)
        # A CAV behind a CAV: same IDM, shorter time gap.
        self.cav_follow_cfg = dict(human_cfg, desired_time_gap_s=float(cav_cfg["desired_time_gap_s"]))
        self.scenario = dict(scenario)
        self.meter_cfg = dict(meter_cfg, mode=self.scenario.get("meter_mode", meter_cfg["mode"]))
        self.time_s = 0.0
        self.vehicles: list[Vehicle] = []
        self.vehicle_counter = 0
        self.mainline_queue: deque[float] = deque()
        self.ramp_queue: deque[float] = deque()
        self.ramp_overflow = 0
        self.exited = 0
        self.generated_mainline = 0
        self.generated_ramp = 0
        self.total_boundary_delay_s = 0.0
        self.total_vehicle_delay_s = 0.0
        self.global_min_gap_m = math.inf
        self.overlap_steps = 0            # vehicle-steps with a negative gap (collision); must stay 0
        self.zipper_ramp_turn = True      # zipper merge: True = the next slot at the merge goes to the ramp
        self.hardest_braking_mps2 = 0.0   # most negative applied acceleration
        self.trajectory_rows: list[dict[str, Any]] = []
        self.observation_rows: list[dict[str, Any]] = []
        self.crossing_rows: list[dict[str, Any]] = []
        self.meter_rows: list[dict[str, Any]] = []
        self.ramp_queue_rows: list[dict[str, Any]] = []
        self.next_log_s = 0.0
        self.next_queue_log_s = 0.0
        self._finalized = False
        self.detectors = [
            DetectorAccumulator(f"D{i+1}", float(x), float(self.cfg["detector_interval_s"]))
            for i, x in enumerate(self.cfg["detector_positions_m"])
        ]
        self.latest_detector_record: dict[str, dict[str, Any]] = {}
        self.meter = RampMeter(self.meter_cfg, float(self.cfg["detector_interval_s"]))
        self.mainline_schedule, self.ramp_schedule = self._demand_schedules()
        self.mainline_idx = 0
        self.ramp_idx = 0

    def _demand_schedules(self) -> tuple[list[float], list[float]]:
        """Poisson arrivals (exponential gaps) at the scenario's mean rates, from their own seeded stream."""
        end = float(self.cfg["demand_end_s"])
        arrivals_rng = random.Random(int(self.cfg["seed"]) + 1)

        def poisson(rate_vph: float) -> list[float]:
            times, t = [], 0.0
            while rate_vph > 0:
                t += arrivals_rng.expovariate(rate_vph / 3600.0)
                if t >= end:
                    break
                times.append(t)
            return times

        return poisson(float(self.scenario["mainline_demand_vph"])), poisson(float(self.scenario["ramp_demand_vph"]))

    def _is_cav(self, vehicle_index: int) -> bool:
        """Each vehicle is a CAV with probability = penetration (own random draw per vehicle index)."""
        penetration = float(self.scenario["penetration"])
        if penetration <= 0.0:
            return False
        if penetration >= 1.0:
            return True
        return random.Random(int(self.cfg["seed"]) * 1000003 + vehicle_index * 9176).random() < penetration

    def _new_vehicle(self, x: float, v: float, source: str, entry_time: float) -> Vehicle:
        idx = self.vehicle_counter
        self.vehicle_counter += 1
        return Vehicle(f"veh_{idx:04d}", x, v, 0.0, source, self._is_cav(idx), entry_time, spawn_time_s=self.time_s)

    def _idm_cfg(self, vehicle: Vehicle, leader: Vehicle | None) -> dict[str, float]:
        """CACC (short CAV time gap) only when both the vehicle and its leader are CAVs."""
        if vehicle.cav and leader is not None and leader.cav:
            return self.cav_follow_cfg
        return self.human_cfg

    def _desired_speed(self, x: float) -> float:
        return float(self.cfg["free_speed_mps"])

    def _merge_safe_decel(self, speed: float) -> float:
        """Largest braking a merge may impose on a vehicle at this speed: merge_safe_decel_mps2 at the desired
        speed, rising linearly to merge_safe_decel_standstill_mps2 at standstill (hard braking is less risky
        when slow). Same rule as the MOBIL code of traffic-simulation.de (Treiber)."""
        rel = min(speed / float(self.cfg["free_speed_mps"]), 1.0)
        return rel * float(self.cfg["merge_safe_decel_mps2"]) + (1.0 - rel) * float(self.cfg["merge_safe_decel_standstill_mps2"])

    def _insertion_is_safe(self, x: float, v: float, cav: bool, ahead: Vehicle | None, behind: Vehicle | None,
                           b_limit) -> bool:
        """A vehicle placed at x with speed v is admitted only if both gaps are at least s0 and, by the
        IDM, neither it nor its new follower would have to brake harder than b_limit(its speed)."""
        length = float(self.cfg["vehicle_length_m"])
        s0 = float(self.human_cfg["minimum_gap_m"])
        candidate = Vehicle("candidate", x, v, 0.0, "candidate", cav, self.time_s)
        if ahead is not None:
            if ahead.x - x - length < s0:
                return False
            a = idm_acceleration(candidate, ahead, self._desired_speed(x), self._idm_cfg(candidate, ahead), length)
            if a < -b_limit(v):
                return False
        if behind is not None:
            if x - behind.x - length < s0:
                return False
            a = idm_acceleration(behind, candidate, self._desired_speed(behind.x), self._idm_cfg(behind, candidate), length)
            if a < -b_limit(behind.v):
                return False
        return True

    def _process_arrivals(self) -> None:
        while self.mainline_idx < len(self.mainline_schedule) and self.mainline_schedule[self.mainline_idx] <= self.time_s + 1e-9:
            self.mainline_queue.append(self.mainline_schedule[self.mainline_idx])
            self.generated_mainline += 1
            self.mainline_idx += 1
        while self.ramp_idx < len(self.ramp_schedule) and self.ramp_schedule[self.ramp_idx] <= self.time_s + 1e-9:
            if len(self.ramp_queue) < int(self.meter_cfg["storage_vehicles"]):
                self.ramp_queue.append(self.ramp_schedule[self.ramp_idx])
            else:
                self.ramp_overflow += 1
            self.generated_ramp += 1
            self.ramp_idx += 1

        if self.mainline_queue:
            # Mainline entry at x = 0 at the speed of the vehicle ahead (at most v0), if safe.
            nearest = min(self.vehicles, key=lambda v: v.x, default=None)
            v_in = min(float(self.cfg["free_speed_mps"]), nearest.v) if nearest else float(self.cfg["free_speed_mps"])
            if self._insertion_is_safe(0.0, v_in, self._is_cav(self.vehicle_counter), nearest, None,
                                       lambda speed: float(self.human_cfg["comfortable_decel_mps2"])):
                arrival = self.mainline_queue.popleft()
                self.vehicles.append(self._new_vehicle(0.0, v_in, "mainline", arrival))

        if self.ramp_queue and self.meter.release_due(self.time_s):
            # Ramp merge at the point x = ramp_position at the speed of its new leader (capped below), if the
            # new follower need not brake harder than the speed-dependent merge limit. The merge is the bottleneck.
            x = float(self.cfg["ramp_position_m"])
            ahead = min((v for v in self.vehicles if v.x >= x), key=lambda v: v.x, default=None)
            behind = max((v for v in self.vehicles if v.x < x), key=lambda v: v.x, default=None)
            # Entry speed is capped: the short acceleration lane does not let ramp vehicles reach v0.
            merge_v = min(ahead.v if ahead else float(self.cfg["free_speed_mps"]), float(self.cfg["merge_speed_max_mps"]))
            if self._insertion_is_safe(x, merge_v, self._is_cav(self.vehicle_counter), ahead, behind, self._merge_safe_decel):
                arrival = self.ramp_queue.popleft()
                self.vehicles.append(self._new_vehicle(x, merge_v, "ramp", arrival))
                self.zipper_ramp_turn = False
            else:
                # Failed gap acceptance does not consume the scheduled release opportunity.
                self.meter.next_release_s = self.time_s + min(1.0, 3600.0 / max(self.meter.rate_vph, 1.0))

    def _zipper_leader(self, vehicle: Vehicle, leader: Vehicle | None) -> Vehicle | None:
        """Zipper merge in slow traffic. If a ramp vehicle is waiting, it is the ramp's turn, and the first
        mainline vehicle within 100 m upstream of the merge drives slower than zipper_speed_mps and can stop
        behind the merge slot with the braking a merge may impose (at most max_braking_mps2), that vehicle
        stops for an imaginary standing car at the merge point. This opens one slot for the ramp vehicle;
        after it merges, the next slot goes to the mainline. A vehicle too close to stop passes, and the next
        one yields."""
        x_merge = float(self.cfg["ramp_position_m"])
        slot_rear = x_merge - float(self.cfg["vehicle_length_m"])
        if not (self.ramp_queue and self.zipper_ramp_turn and vehicle.x < x_merge
                and (leader is None or leader.x >= x_merge)
                and x_merge - vehicle.x < 100.0 and vehicle.v < float(self.cfg["zipper_speed_mps"])
                # only a vehicle that can still stop behind the slot yields
                and slot_rear - vehicle.x - float(self.human_cfg["minimum_gap_m"])
                >= vehicle.v ** 2 / (2.0 * min(self._merge_safe_decel(vehicle.v), float(self.cfg["max_braking_mps2"])))):
            return leader
        return Vehicle("zipper_slot", x_merge, 0.0, 0.0, "virtual", False, self.time_s)

    def _leaders(self) -> list[Vehicle | None]:
        """Leader of each vehicle (vehicles sorted by position), with the zipper slot where it applies."""
        self.vehicles.sort(key=lambda v: v.x)
        leaders = []
        for i, vehicle in enumerate(self.vehicles):
            leader = self.vehicles[i + 1] if i + 1 < len(self.vehicles) else None
            leaders.append(self._zipper_leader(vehicle, leader))
        return leaders

    def _advance(self) -> None:
        dt = float(self.cfg["dt_s"])
        length = float(self.cfg["vehicle_length_m"])
        leaders = self._leaders()
        commands = [idm_acceleration(v, leader, self._desired_speed(v.x), self._idm_cfg(v, leader), length)
                    for v, leader in zip(self.vehicles, leaders)]
        x_merge = float(self.cfg["ramp_position_m"])
        for vehicle, cmd in zip(self.vehicles, commands):
            a_new = max(cmd, -float(self.cfg["max_braking_mps2"]))  # IDM, within physical braking
            if vehicle.v + a_new * dt < 0.0:
                # It would roll backwards within the step: it stops instead.
                x_new = vehicle.x - vehicle.v * vehicle.v / (2.0 * a_new)
                v_new = 0.0
            else:
                v_new = vehicle.v + a_new * dt
                x_new = vehicle.x + vehicle.v * dt + 0.5 * a_new * dt * dt
            if vehicle.x < x_merge <= x_new:
                self.zipper_ramp_turn = True
            for detector in self.detectors:
                if vehicle.x < detector.position_m <= x_new:
                    detector.crossing(vehicle.vehicle_id, v_new)
                    self.crossing_rows.append({"time_s": self.time_s + dt, "sensor_id": detector.sensor_id,
                                               "vehicle_id": vehicle.vehicle_id, "crossing_speed_mps": v_new})
            vehicle.x, vehicle.v, vehicle.a = x_new, v_new, a_new
            self.hardest_braking_mps2 = min(self.hardest_braking_mps2, a_new)
            desired = max(self._desired_speed(vehicle.x), 0.1)
            vehicle.accumulated_delay_s += max(0.0, 1.0 - vehicle.v / desired) * dt

        # Collisions are counted, not prevented.
        self.vehicles.sort(key=lambda v: v.x)
        for i in range(len(self.vehicles) - 1):
            gap = self.vehicles[i + 1].x - self.vehicles[i].x - length
            self.vehicles[i].min_gap_m = min(self.vehicles[i].min_gap_m, gap)
            self.global_min_gap_m = min(self.global_min_gap_m, gap)
            if gap < 0.0:
                self.overlap_steps += 1

        remaining = []
        for v in self.vehicles:
            if v.x >= float(self.cfg["road_length_m"]):
                self.exited += 1
                self.total_vehicle_delay_s += v.accumulated_delay_s
            else:
                remaining.append(v)
        self.vehicles = remaining

    def _close_detector_intervals(self) -> None:
        interval = float(self.cfg["detector_interval_s"])
        if self.time_s <= 0.0 or abs((self.time_s / interval) - round(self.time_s / interval)) > 1e-7:
            return
        for detector in self.detectors:
            row = detector.close_interval(self.time_s)
            self.observation_rows.append(row)
            self.latest_detector_record[detector.sensor_id] = row

    def _update_meter(self) -> None:
        downstream = self.latest_detector_record.get("D2")   # ALINEA uses the occupancy downstream of the merge
        row = self.meter.update(self.time_s, downstream, len(self.ramp_queue))
        if row is not None:
            self.meter_rows.append(row)

    def _log_state(self) -> None:
        if self.time_s + 1e-9 >= self.next_log_s:
            self.next_log_s += float(self.cfg["log_interval_s"])
            for v in self.vehicles:
                self.trajectory_rows.append({"time_s": round(self.time_s, 3), "vehicle_id": v.vehicle_id,
                                             "position_m": v.x, "speed_mps": v.v, "acceleration_mps2": v.a,
                                             "source": v.source, "cav": v.cav})
        if self.time_s + 1e-9 >= self.next_queue_log_s:
            self.next_queue_log_s += 1.0
            self.ramp_queue_rows.append({"time_s": round(self.time_s, 3), "ramp_queue_veh": len(self.ramp_queue),
                                         "mainline_boundary_queue_veh": len(self.mainline_queue),
                                         "meter_rate_vph": self.meter.rate_vph})

    def step(self) -> None:
        """Advance one time step (the batch runs and the live view use this same path)."""
        if self._finalized or self.time_s >= float(self.cfg["duration_s"]) - 1e-9:
            return
        dt = float(self.cfg["dt_s"])
        self._process_arrivals()
        self._close_detector_intervals()
        self._update_meter()
        for detector in self.detectors:
            detector.sample_occupancy(self.vehicles, float(self.cfg["vehicle_length_m"]), dt)
        self._log_state()
        self._advance()
        self.total_boundary_delay_s += (len(self.mainline_queue) + len(self.ramp_queue)) * dt
        self.time_s = round(self.time_s + dt, 10)

    def snapshot(self) -> dict[str, Any]:
        """Compact, JSON-safe view for the live visualization."""
        length = float(self.cfg["vehicle_length_m"])
        ordered = sorted(self.vehicles, key=lambda vehicle: vehicle.x)
        vehicles = []
        for index, vehicle in enumerate(ordered):
            leader = ordered[index + 1] if index + 1 < len(ordered) else None
            cacc = self._idm_cfg(vehicle, leader) is self.cav_follow_cfg
            vehicles.append({
                "vehicle_id": vehicle.vehicle_id,
                "x_m": round(vehicle.x, 3),
                "speed_mps": round(vehicle.v, 3),
                "acceleration_mps2": round(vehicle.a, 3),
                "gap_m": None if leader is None else round(leader.x - vehicle.x - length, 3),
                "source": vehicle.source,
                "age_since_spawn_s": round(max(0.0, self.time_s - vehicle.spawn_time_s), 3),
                "controller": "cav" if vehicle.cav else "human",
                "control_state": "CACC (short gap)" if cacc else "IDM (human gap)",
                "message_valid": cacc,
                "hard_braking": vehicle.a < -3.0,
            })
        elapsed = max(self.time_s, float(self.cfg["dt_s"]))
        active_delay = sum(vehicle.accumulated_delay_s for vehicle in self.vehicles)
        total_delay = self.total_vehicle_delay_s + active_delay + self.total_boundary_delay_s
        detector_records = []
        for detector in self.detectors:
            record = self.latest_detector_record.get(detector.sensor_id, {})
            speed = record.get("mean_speed_mps")
            occupancy = record.get("occupancy_pct")
            detector_records.append({
                "sensor_id": detector.sensor_id,
                "position_m": detector.position_m,
                "count": int(record.get("count", 0)),
                "mean_speed_mps": round(float(speed), 3) if speed is not None and np.isfinite(speed) else None,
                "occupancy_pct": round(float(occupancy), 3) if occupancy is not None and np.isfinite(occupancy) else None,
            })
        mean_speed = float(np.mean([vehicle.v for vehicle in self.vehicles])) if self.vehicles else 0.0
        minimum_gap = self.global_min_gap_m if math.isfinite(self.global_min_gap_m) else None
        return {
            "scenario_id": self.scenario["scenario_id"],
            "time_s": round(self.time_s, 3),
            "duration_s": float(self.cfg["duration_s"]),
            "dt_s": float(self.cfg["dt_s"]),
            "finished": self.time_s >= float(self.cfg["duration_s"]) - 1e-9,
            "vehicles": vehicles,
            "queues": {"mainline": len(self.mainline_queue), "ramp": len(self.ramp_queue), "ramp_overflow": self.ramp_overflow},
            "metrics": {
                "active_vehicles": len(self.vehicles),
                "exited_vehicles": self.exited,
                "throughput_veh_h": round(self.exited * 3600.0 / elapsed, 2),
                "total_delay_veh_h": round(total_delay / 3600.0, 4),
                "mean_speed_mps": round(mean_speed, 3),
                "minimum_gap_m": round(minimum_gap, 3) if minimum_gap is not None else None,
                "hardest_braking_mps2": round(self.hardest_braking_mps2, 3),
                "meter_rate_vph": round(self.meter.rate_vph, 1),
            },
            "detectors": detector_records,
            "road": {"length_m": float(self.cfg["road_length_m"]),
                     "ramp_position_m": float(self.cfg["ramp_position_m"]), "vehicle_length_m": length},
        }

    def _finalize(self) -> None:
        if self._finalized:
            return
        self._close_detector_intervals()
        self.total_vehicle_delay_s += sum(v.accumulated_delay_s for v in self.vehicles)
        self._finalized = True

    def run(self) -> dict[str, Any]:
        duration = float(self.cfg["duration_s"])
        while self.time_s < duration - 1e-9:
            self.step()
        self._finalize()
        unfinished = len(self.vehicles) + len(self.mainline_queue) + len(self.ramp_queue) + self.ramp_overflow
        return {
            "scenario_id": self.scenario["scenario_id"],
            "seed": int(self.cfg["seed"]),
            "penetration": float(self.scenario["penetration"]),
            "dt_s": float(self.cfg["dt_s"]),
            "generated_vehicles": self.generated_mainline + self.generated_ramp,
            "exited_vehicles": self.exited,
            "unfinished_vehicles": unfinished,
            "ramp_overflow_vehicles": self.ramp_overflow,
            "total_delay_veh_h": (self.total_vehicle_delay_s + self.total_boundary_delay_s) / 3600.0,
            "minimum_gap_m": self.global_min_gap_m,
            "overlap_steps": self.overlap_steps,
            "hardest_braking_mps2": self.hardest_braking_mps2,
        }

    def tables(self) -> dict[str, pd.DataFrame]:
        return {
            "trajectories": pd.DataFrame(self.trajectory_rows),
            "observations": pd.DataFrame(self.observation_rows),
            "crossings": pd.DataFrame(self.crossing_rows),
            "meter": pd.DataFrame(self.meter_rows),
            "queues": pd.DataFrame(self.ramp_queue_rows),
        }
