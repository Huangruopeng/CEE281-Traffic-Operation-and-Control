"""Core microscopic simulator, observation interfaces, and vehicle controllers.

Internal units are seconds, metres, metres/second, and metres/second^2.
The controller receives only current local measurements and delayed messages.
Simulator truth is written separately for evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict, deque
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
    source: str
    equipped: bool
    controller: str
    entry_time: float
    spawn_time_s: float = 0.0
    command_a: float = 0.0
    next_control_time: float = 0.0
    last_message_a: float = 0.0
    last_message_time: float = -math.inf
    accumulated_delay_s: float = 0.0
    min_gap_m: float = math.inf
    hard_braking: bool = False
    hard_brake_events: int = 0
    last_control_state: str = "initializing"
    last_message_valid: bool = False
    last_message_age_s: float = math.nan
    last_gap_m: float = math.inf
    last_relative_speed_mps: float = math.nan
    safety_override_active: bool = False
    collision_guard_active: bool = False


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

    def close_interval(self, end_s: float, quality_flag: str = "ok") -> dict[str, Any]:
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
            "quality_flag": quality_flag,
        }
        self.interval_start_s = end_s
        self.crossing_speeds.clear()
        self.crossing_ids.clear()
        self.occupancy_sum_pct_s = 0.0
        return row


class RampMeter:
    """Fixed or ALINEA-like feedback ramp-release controller."""

    def __init__(self, cfg: dict[str, Any], update_s: float):
        self.cfg = cfg
        self.update_s = update_s
        self.mode = cfg["mode"]
        self.rate_vph = float(cfg["initial_rate_vph"])
        self.next_update_s = 0.0
        self.next_release_s = 0.0
        self.last_observation: dict[str, Any] | None = None

    def update(
        self,
        time_s: float,
        observation: dict[str, Any] | None,
        queue_estimate: int,
        sensor_ok: bool = True,
    ) -> dict[str, Any] | None:
        if time_s + 1e-9 < self.next_update_s:
            return None
        self.next_update_s = time_s + self.update_s
        self.last_observation = observation
        fallback = False
        if self.mode == "unmetered":
            self.rate_vph = 1800.0
            reason = "unmetered baseline"
        elif self.mode == "fixed":
            self.rate_vph = float(self.cfg["fixed_rate_vph"])
            reason = "fixed-time release"
        elif not sensor_ok or observation is None or not np.isfinite(observation.get("occupancy_pct", np.nan)):
            self.rate_vph = float(self.cfg["fixed_rate_vph"])
            fallback = True
            reason = "missing observation: fixed-rate fallback"
        else:
            error = float(self.cfg["target_occupancy_pct"]) - float(observation["occupancy_pct"])
            self.rate_vph += float(self.cfg["alinea_gain_vph_per_pct"]) * error
            reason = "ALINEA-like occupancy feedback"
            if queue_estimate >= int(self.cfg["queue_override_vehicles"]):
                self.rate_vph = float(self.cfg["maximum_rate_vph"])
                reason = "ramp storage override"
        self.rate_vph = float(np.clip(
            self.rate_vph,
            self.cfg["minimum_rate_vph"],
            self.cfg["maximum_rate_vph"],
        ))
        return {
            "issue_time_s": round(time_s, 3),
            "apply_time_s": round(time_s, 3),
            "actuator_id": "ramp_meter_R1",
            "action": "release_rate",
            "value": self.rate_vph,
            "units": "veh/h",
            "lower_bound": float(self.cfg["minimum_rate_vph"]),
            "upper_bound": float(self.cfg["maximum_rate_vph"]),
            "fallback_active": fallback,
            "reason": reason,
            "queue_estimate_veh": int(queue_estimate),
        }

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


def automated_command(
    vehicle: Vehicle,
    leader: Vehicle | None,
    desired_speed_mps: float,
    cfg: dict[str, float],
    vehicle_length_m: float,
    feedforward_a: float,
) -> tuple[float, dict[str, float]]:
    """Constant-time-headway PD controller with optional predecessor feedforward."""
    speed_cmd = float(cfg["speed_gain_per_s"]) * (desired_speed_mps - vehicle.v)
    if leader is None:
        raw = speed_cmd
        gap = math.inf
        spacing_error = math.nan
        relative_speed = math.nan
    else:
        gap = leader.x - vehicle.x - vehicle_length_m
        desired_gap = float(cfg["standstill_gap_m"]) + float(cfg["desired_time_gap_s"]) * vehicle.v
        spacing_error = gap - desired_gap
        relative_speed = leader.v - vehicle.v
        gap_cmd = (
            float(cfg["kp_per_s2"]) * spacing_error
            + float(cfg["kd_per_s"]) * relative_speed
            + float(cfg["feedforward_gain"]) * feedforward_a
        )
        raw = min(speed_cmd, gap_cmd)
        # Explicit local emergency fallback, independent of communication.
        if gap < max(0.5, 0.35 * desired_gap) and relative_speed < 0.0:
            raw = float(cfg["maximum_brake_mps2"])
    bounded = float(np.clip(raw, cfg["maximum_brake_mps2"], cfg["maximum_accel_mps2"]))
    return bounded, {
        "gap_m": gap,
        "spacing_error_m": spacing_error,
        "relative_speed_mps": relative_speed,
        "feedforward_accel_mps2": feedforward_a,
        "unbounded_command_mps2": raw,
    }


class FreewaySimulation:
    def __init__(
        self,
        sim_cfg: dict[str, Any],
        human_cfg: dict[str, Any],
        auto_cfg: dict[str, Any],
        meter_cfg: dict[str, Any],
        scenario: dict[str, Any],
    ):
        self.cfg = dict(sim_cfg)
        self.human_cfg = dict(human_cfg)
        self.auto_cfg = dict(auto_cfg)
        self.meter_cfg = dict(meter_cfg)
        self.scenario = dict(scenario)
        self.rng = random.Random(int(self.cfg["seed"]))
        self.time_s = 0.0
        self.vehicles: list[Vehicle] = []
        self.vehicle_counter = 0
        self.mainline_queue: deque[float] = deque()
        self.ramp_queue: deque[float] = deque()
        self.unmet_mainline = 0
        self.unmet_ramp = 0
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
        self.hard_brake_events = 0
        self.message_attempts = 0
        self.message_received = 0
        self.message_fallbacks = 0
        self.safety_interventions = 0
        self.collision_guard_activations = 0
        self.disturbance_vehicle_id: str | None = None
        self.disturbance_cohort: list[str] = []
        self.message_history: dict[str, deque[tuple[float, float]]] = defaultdict(lambda: deque(maxlen=80))
        self.trajectory_rows: list[dict[str, Any]] = []
        self.observation_rows: list[dict[str, Any]] = []
        self.crossing_rows: list[dict[str, Any]] = []
        self.command_rows: list[dict[str, Any]] = []
        self.decision_rows: list[dict[str, Any]] = []
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
        self._create_initial_platoon()

    def _demand_schedules(self) -> tuple[list[float], list[float]]:
        high = self.scenario["demand"] == "high"
        main_rate = float(self.scenario.get("mainline_demand_vph",
                          self.cfg["high_mainline_demand_vph"] if high else self.cfg["mainline_demand_vph"]))
        ramp_rate = float(self.scenario.get("ramp_demand_vph",
                          self.cfg["high_ramp_demand_vph"] if high else self.cfg["ramp_demand_vph"]))
        end = float(self.cfg["demand_end_s"])
        if self.scenario.get("arrival_process") == "poisson":
            # Random arrivals with the same mean rate: exponential gaps, own seeded stream.
            arrivals_rng = random.Random(int(self.cfg["seed"]) + 1)

            def poisson(rate_vph: float) -> list[float]:
                times, t = [], 0.0
                while rate_vph > 0:
                    t += arrivals_rng.expovariate(rate_vph / 3600.0)
                    if t >= end:
                        break
                    times.append(t)
                return times

            return poisson(main_rate), poisson(ramp_rate)
        main = list(np.arange(1.0, end, 3600.0 / main_rate)) if main_rate > 0 else []
        ramp = list(np.arange(3.0, end, 3600.0 / ramp_rate)) if ramp_rate > 0 else []
        return main, ramp

    def _is_equipped(self, vehicle_index: int) -> bool:
        penetration = float(self.scenario["penetration"])
        if penetration <= 0.0:
            return False
        if penetration >= 1.0:
            return True
        nested_rng = random.Random(int(self.cfg["seed"]) * 1000003 + vehicle_index * 9176)
        return nested_rng.random() < penetration

    def _new_vehicle(self, x: float, v: float, source: str, entry_time: float) -> Vehicle:
        idx = self.vehicle_counter
        self.vehicle_counter += 1
        equipped = self._is_equipped(idx)
        requested = self.scenario["controller"]
        controller = requested if equipped and requested in {"acc", "cacc"} else "human"
        return Vehicle(
            vehicle_id=f"veh_{idx:04d}",
            x=x,
            v=v,
            a=0.0,
            source=source,
            equipped=equipped,
            controller=controller,
            entry_time=entry_time,
            spawn_time_s=self.time_s,
        )

    def _create_initial_platoon(self) -> None:
        n = int(self.cfg["initial_platoon_size"])
        spacing = float(self.cfg["initial_spacing_m"])
        front_x = 600.0
        for i in range(n):
            x = front_x - (n - 1 - i) * spacing
            self.vehicles.append(self._new_vehicle(x, float(self.cfg["initial_speed_mps"]), "initial", 0.0))
        self.vehicles.sort(key=lambda v: v.x)

    def _desired_speed(self, x: float) -> float:
        return float(self.cfg["free_speed_mps"])

    def _merge_safe_decel(self, speed: float) -> float:
        """Largest braking a merge may impose on a vehicle at this speed: merge_safe_decel_mps2 at the desired
        speed, rising linearly to merge_safe_decel_standstill_mps2 at standstill (hard braking is less risky
        when slow). Same rule as the MOBIL code of traffic-simulation.de (Treiber)."""
        rel = min(speed / float(self.cfg["free_speed_mps"]), 1.0)
        return rel * float(self.cfg["merge_safe_decel_mps2"]) + (1.0 - rel) * float(self.cfg["merge_safe_decel_standstill_mps2"])

    def _insertion_is_safe(self, x: float, v: float, ahead: Vehicle | None, behind: Vehicle | None,
                           b_limit) -> bool:
        """A vehicle placed at x with speed v is admitted only if both gaps are at least s0 and, by the
        IDM, neither it nor its new follower would have to brake harder than b_limit(its speed)."""
        length = float(self.cfg["vehicle_length_m"])
        s0 = float(self.human_cfg["minimum_gap_m"])
        candidate = Vehicle("candidate", x, v, 0.0, "candidate", False, "human", self.time_s)
        if ahead is not None:
            if ahead.x - x - length < s0:
                return False
            a = idm_acceleration(candidate, ahead, self._desired_speed(x), self.human_cfg, length)
            if a < -b_limit(v):
                return False
        if behind is not None:
            if x - behind.x - length < s0:
                return False
            a = idm_acceleration(behind, candidate, self._desired_speed(behind.x), self.human_cfg, length)
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
            if self._insertion_is_safe(0.0, v_in, nearest, None, lambda speed: float(self.human_cfg["comfortable_decel_mps2"])):
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
            if self._insertion_is_safe(x, merge_v, ahead, behind, self._merge_safe_decel):
                arrival = self.ramp_queue.popleft()
                self.vehicles.append(self._new_vehicle(x, merge_v, "ramp", arrival))
                self.zipper_ramp_turn = False
            else:
                # Failed gap acceptance does not consume the scheduled release opportunity.
                self.meter.next_release_s = self.time_s + min(1.0, 3600.0 / max(self.meter.rate_vph, 1.0))

    def _select_disturbance_cohort(self) -> None:
        if self.disturbance_vehicle_id is not None:
            return
        target = min(self.vehicles, key=lambda v: abs(v.x - 750.0), default=None)
        if target is None:
            return
        self.disturbance_vehicle_id = target.vehicle_id
        ordered = sorted(self.vehicles, key=lambda v: v.x, reverse=True)
        idx = next(i for i, v in enumerate(ordered) if v.vehicle_id == target.vehicle_id)
        self.disturbance_cohort = [v.vehicle_id for v in ordered[idx:idx + 9]]

    def _message_for(self, leader: Vehicle, receiver: Vehicle) -> tuple[float, bool, float]:
        if receiver.controller != "cacc" or not leader.equipped:
            return 0.0, False, math.inf
        self.message_attempts += 1
        if self.rng.random() < float(self.scenario["dropout_probability"]):
            self.message_fallbacks += 1
            age = self.time_s - receiver.last_message_time
            if age <= float(self.auto_cfg["message_stale_after_s"]):
                return receiver.last_message_a, True, age
            return 0.0, False, age
        delay = float(self.scenario["comm_delay_s"])
        target_time = self.time_s - delay
        history = self.message_history.get(leader.vehicle_id, deque())
        candidates = [item for item in history if item[0] <= target_time + 1e-9]
        if not candidates:
            self.message_fallbacks += 1
            return 0.0, False, math.inf
        msg_t, msg_a = candidates[-1]
        receiver.last_message_a = msg_a
        receiver.last_message_time = self.time_s
        self.message_received += 1
        return msg_a, True, self.time_s - msg_t

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
        return Vehicle("zipper_slot", x_merge, 0.0, 0.0, "virtual", False, "human", self.time_s)

    def _compute_commands(self) -> dict[str, float]:
        self.vehicles.sort(key=lambda v: v.x)
        commands: dict[str, float] = {}
        disturbance_t = float(self.cfg["disturbance_time_s"])
        if self.time_s + 1e-9 >= disturbance_t:
            self._select_disturbance_cohort()
        for i, vehicle in enumerate(self.vehicles):
            leader = self.vehicles[i + 1] if i + 1 < len(self.vehicles) else None
            leader = self._zipper_leader(vehicle, leader)
            desired_speed = self._desired_speed(vehicle.x)
            if vehicle.controller == "human":
                cmd = idm_acceleration(vehicle, leader, desired_speed, self.human_cfg, float(self.cfg["vehicle_length_m"]))
                detail = {"gap_m": math.inf if leader is None else leader.x - vehicle.x - float(self.cfg["vehicle_length_m"]), "spacing_error_m": math.nan, "relative_speed_mps": math.nan, "feedforward_accel_mps2": 0.0, "unbounded_command_mps2": cmd}
                source = "IDM"
                msg_valid = False
                msg_age = math.nan
                vehicle.last_control_state = source
                vehicle.last_message_valid = False
                vehicle.last_message_age_s = math.nan
                vehicle.last_gap_m = detail["gap_m"]
                vehicle.last_relative_speed_mps = detail["relative_speed_mps"]
            elif self.time_s + 1e-9 >= vehicle.next_control_time:
                ff = 0.0
                msg_valid = False
                msg_age = math.nan
                if leader is not None:
                    ff, msg_valid, msg_age = self._message_for(leader, vehicle)
                cmd, detail = automated_command(
                    vehicle, leader, desired_speed, self.auto_cfg,
                    float(self.cfg["vehicle_length_m"]), ff,
                )
                vehicle.command_a = cmd
                vehicle.next_control_time = self.time_s + float(self.cfg["control_update_s"])
                source = "CACC" if vehicle.controller == "cacc" and msg_valid else "ACC_fallback" if vehicle.controller == "cacc" else "ACC"
                vehicle.last_control_state = source
                vehicle.last_message_valid = msg_valid
                vehicle.last_message_age_s = msg_age
                vehicle.last_gap_m = detail["gap_m"]
                vehicle.last_relative_speed_mps = detail["relative_speed_mps"]
                if vehicle.vehicle_id in self.disturbance_cohort or (len(self.decision_rows) < 120 and vehicle.equipped):
                    self.decision_rows.append({
                        "issue_time_s": round(self.time_s, 3),
                        "apply_time_s": round(self.time_s, 3),
                        "vehicle_id": vehicle.vehicle_id,
                        "controller": vehicle.controller,
                        "measured_ego_speed_mps": vehicle.v,
                        "measured_gap_m": detail["gap_m"],
                        "measured_relative_speed_mps": detail["relative_speed_mps"],
                        "communicated_predecessor_accel_mps2": detail["feedforward_accel_mps2"],
                        "message_valid": msg_valid,
                        "message_age_s": msg_age,
                        "command_mps2": cmd,
                        "bounded_min_mps2": float(self.auto_cfg["maximum_brake_mps2"]),
                        "bounded_max_mps2": float(self.auto_cfg["maximum_accel_mps2"]),
                        "fallback_state": source,
                    })
            else:
                cmd = vehicle.command_a
                detail = {}
                source = vehicle.controller.upper()
                msg_valid = False
                msg_age = math.nan

            # The exogenous brake profile is applied only to the selected leader.
            duration = float(self.cfg["disturbance_duration_s"])
            if (
                vehicle.vehicle_id == self.disturbance_vehicle_id
                and disturbance_t <= self.time_s < disturbance_t + duration
            ):
                cmd = float(self.cfg["strong_disturbance_decel_mps2"] if self.scenario["disturbance"] == "strong" else self.cfg["disturbance_decel_mps2"])
                vehicle.command_a = cmd
                vehicle.last_control_state = "disturbance_brake"
            # The safety supervisor belongs to the automated controller; human drivers stay pure IDM.
            if vehicle.equipped:
                safe_cmd, safety_active = self._safety_limited_command(vehicle, leader, float(cmd))
            else:
                safe_cmd, safety_active = float(cmd), False
            if safety_active and not vehicle.safety_override_active:
                self.safety_interventions += 1
            vehicle.safety_override_active = safety_active
            if safety_active:
                vehicle.last_control_state = "safety_override"
                if self.decision_rows and self.decision_rows[-1].get("vehicle_id") == vehicle.vehicle_id and self.decision_rows[-1].get("issue_time_s") == round(self.time_s, 3):
                    self.decision_rows[-1]["command_mps2"] = safe_cmd
                    self.decision_rows[-1]["fallback_state"] = "safety_override"
            vehicle.command_a = safe_cmd
            commands[vehicle.vehicle_id] = safe_cmd
        return commands

    def _safety_limited_command(
        self,
        vehicle: Vehicle,
        leader: Vehicle | None,
        requested_accel: float,
    ) -> tuple[float, bool]:
        """Limit a command so the follower preserves the physical gap.

        The supervisor combines a one-step gap constraint with a braking-distance
        constraint.  The normal IDM/ACC/CACC command is unchanged unless it would
        consume the configured physical clearance.
        """
        if leader is None:
            return requested_accel, False
        dt = float(self.cfg["dt_s"])
        length = float(self.cfg["vehicle_length_m"])
        minimum_gap = float(self.cfg.get("minimum_physical_gap_m", 2.0))
        maximum_brake = float(self.auto_cfg["maximum_brake_mps2"])
        maximum_accel = float(
            self.auto_cfg["maximum_accel_mps2"]
            if vehicle.equipped else self.human_cfg["maximum_accel_mps2"]
        )
        gap = leader.x - vehicle.x - length
        if gap <= minimum_gap:
            return maximum_brake, True

        # Preserve the minimum gap over the next ballistic integration step.
        assumed_leader_a = min(leader.a, 0.0)
        one_step_bound = assumed_leader_a + 2.0 * (
            gap - minimum_gap + (leader.v - vehicle.v) * dt
        ) / (dt * dt)
        one_step_risk = one_step_bound < vehicle.a - 1e-9

        # Intervene on stopping distance only when the available clearance is
        # actually exhausted; a harmless speed difference at a long gap must
        # not suppress the nominal controller.
        braking_magnitude = max(abs(maximum_brake), 1e-6)
        available = max(gap - minimum_gap, 1e-6)
        stopping_bound = maximum_accel
        stopping_risk = False
        if vehicle.v > leader.v:
            required_distance = (
                (vehicle.v * vehicle.v - leader.v * leader.v) / (2.0 * braking_magnitude)
                + (vehicle.v - leader.v) * dt
            )
            if required_distance >= available:
                stopping_risk = True
                stopping_bound = (leader.v * leader.v - vehicle.v * vehicle.v) / (2.0 * available)

        safe_command = float(np.clip(
            min(requested_accel, one_step_bound, stopping_bound),
            maximum_brake,
            maximum_accel,
        ))
        return safe_command, one_step_risk or stopping_risk

    def _advance(self, commands: dict[str, float]) -> None:
        dt = float(self.cfg["dt_s"])
        length = float(self.cfg["vehicle_length_m"])
        old_x = {v.vehicle_id: v.x for v in self.vehicles}
        proposals: dict[str, tuple[float, float, float]] = {}
        for vehicle in self.vehicles:
            cmd = commands[vehicle.vehicle_id]
            if vehicle.controller in {"acc", "cacc"}:
                tau = max(float(self.auto_cfg["actuation_time_constant_s"]), dt)
                a_new = vehicle.a + (cmd - vehicle.a) * dt / tau
                if vehicle.safety_override_active:
                    a_new = min(a_new, cmd)
                a_new = float(np.clip(a_new, self.auto_cfg["maximum_brake_mps2"], self.auto_cfg["maximum_accel_mps2"]))
            else:
                a_new = max(cmd, -float(self.cfg["max_braking_mps2"]))  # human: IDM, within physical braking
            if vehicle.v + a_new * dt < 0.0:
                # It would roll backwards within the step: it stops instead.
                x_new = vehicle.x - vehicle.v * vehicle.v / (2.0 * a_new)
                v_new = 0.0
            else:
                v_new = vehicle.v + a_new * dt
                x_new = vehicle.x + vehicle.v * dt + 0.5 * a_new * dt * dt
            proposals[vehicle.vehicle_id] = (x_new, v_new, a_new)

        # Final numerical invariant for automated vehicles only: the configured physical clearance is
        # never crossed. Human drivers are not corrected; any overlap is counted in overlap_steps.
        ordered = sorted(self.vehicles, key=lambda v: v.x, reverse=True)
        leader_x_new = math.inf
        leader_v_new = math.inf
        minimum_gap = float(self.cfg.get("minimum_physical_gap_m", 2.0))
        for vehicle in ordered:
            x_new, v_new, a_new = proposals[vehicle.vehicle_id]
            guard_active = False
            if leader_x_new < math.inf and vehicle.controller in {"acc", "cacc"}:
                max_x = leader_x_new - length - minimum_gap
                if x_new > max_x:
                    x_new = max_x
                    v_new = min(v_new, leader_v_new)
                    a_new = min(a_new, (v_new - vehicle.v) / dt)
                    guard_active = True
            if guard_active and not vehicle.collision_guard_active:
                self.collision_guard_activations += 1
            vehicle.collision_guard_active = guard_active
            proposals[vehicle.vehicle_id] = (x_new, v_new, a_new)
            leader_x_new, leader_v_new = x_new, v_new

        x_merge = float(self.cfg["ramp_position_m"])
        for vehicle in self.vehicles:
            x_new, v_new, a_new = proposals[vehicle.vehicle_id]
            if old_x[vehicle.vehicle_id] < x_merge <= x_new:
                self.zipper_ramp_turn = True
            for detector in self.detectors:
                if old_x[vehicle.vehicle_id] < detector.position_m <= x_new:
                    detector.crossing(vehicle.vehicle_id, v_new)
                    self.crossing_rows.append({
                        "time_s": self.time_s + dt,
                        "sensor_id": detector.sensor_id,
                        "vehicle_id": vehicle.vehicle_id,
                        "crossing_speed_mps": v_new,
                    })
            vehicle.x, vehicle.v, vehicle.a = x_new, v_new, a_new
            self.hardest_braking_mps2 = min(self.hardest_braking_mps2, a_new)
            desired = max(self._desired_speed(vehicle.x), 0.1)
            vehicle.accumulated_delay_s += max(0.0, 1.0 - vehicle.v / desired) * dt
            hard = vehicle.a < -3.0
            if hard and not vehicle.hard_braking:
                vehicle.hard_brake_events += 1
                self.hard_brake_events += 1
            vehicle.hard_braking = hard
            self.message_history[vehicle.vehicle_id].append((self.time_s + dt, vehicle.a))

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
        downstream = self.latest_detector_record.get("D1")
        command = self.meter.update(self.time_s, downstream, len(self.ramp_queue), sensor_ok=True)
        if command is not None:
            self.command_rows.append(command)

    def _log_state(self) -> None:
        if self.time_s + 1e-9 < self.next_log_s:
            return
        self.next_log_s += float(self.cfg["log_interval_s"])
        cohort = set(self.disturbance_cohort)
        for v in self.vehicles:
            if (
                self.cfg.get("log_all_vehicles", False)
                or v.vehicle_id in cohort
                or abs(v.x - float(self.cfg["ramp_position_m"])) < 350.0
                or (v.source == "initial" and self.time_s <= 30.0)
            ):
                self.trajectory_rows.append({
                    "time_s": round(self.time_s, 3),
                    "vehicle_id": v.vehicle_id,
                    "lane_id": "mainline_1",
                    "position_m": v.x,
                    "speed_mps": v.v,
                    "acceleration_mps2": v.a,
                    "controller": v.controller,
                    "equipped": v.equipped,
                    "is_disturbance_cohort": v.vehicle_id in cohort,
                })
        if self.time_s + 1e-9 >= self.next_queue_log_s:
            self.next_queue_log_s += 1.0
            self.ramp_queue_rows.append({
                "time_s": round(self.time_s, 3),
                "ramp_queue_veh": len(self.ramp_queue),
                "mainline_boundary_queue_veh": len(self.mainline_queue),
                "meter_rate_vph": self.meter.rate_vph,
            })

    def step(self) -> None:
        """Advance one model time step using the same path as batch experiments."""
        if self._finalized or self.time_s >= float(self.cfg["duration_s"]) - 1e-9:
            return
        dt = float(self.cfg["dt_s"])
        self._process_arrivals()
        self._close_detector_intervals()
        self._update_meter()
        for detector in self.detectors:
            detector.sample_occupancy(self.vehicles, float(self.cfg["vehicle_length_m"]), dt)
        self._log_state()
        commands = self._compute_commands()
        self._advance(commands)
        self.total_boundary_delay_s += (len(self.mainline_queue) + len(self.ramp_queue)) * dt
        self.time_s = round(self.time_s + dt, 10)

    def snapshot(self) -> dict[str, Any]:
        """Return a compact, JSON-safe view for live visualization."""
        length = float(self.cfg["vehicle_length_m"])
        ordered = sorted(self.vehicles, key=lambda vehicle: vehicle.x)
        vehicles = []
        for index, vehicle in enumerate(ordered):
            leader = ordered[index + 1] if index + 1 < len(ordered) else None
            gap = leader.x - vehicle.x - length if leader is not None else None
            age = vehicle.last_message_age_s
            vehicles.append({
                "vehicle_id": vehicle.vehicle_id,
                "x_m": round(vehicle.x, 3),
                "speed_mps": round(vehicle.v, 3),
                "acceleration_mps2": round(vehicle.a, 3),
                "command_mps2": round(vehicle.command_a, 3),
                "gap_m": None if gap is None else round(gap, 3),
                "source": vehicle.source,
                "age_since_spawn_s": round(max(0.0, self.time_s - vehicle.spawn_time_s), 3),
                "controller": vehicle.controller,
                "equipped": vehicle.equipped,
                "control_state": vehicle.last_control_state,
                "message_valid": vehicle.last_message_valid,
                "message_age_s": round(age, 3) if math.isfinite(age) else None,
                "hard_braking": vehicle.hard_braking,
                "safety_override_active": vehicle.safety_override_active,
                "is_disturbance_vehicle": vehicle.vehicle_id == self.disturbance_vehicle_id,
                "is_disturbance_cohort": vehicle.vehicle_id in self.disturbance_cohort,
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
        message_success = self.message_received / self.message_attempts if self.message_attempts else None
        return {
            "scenario_id": self.scenario["scenario_id"],
            "time_s": round(self.time_s, 3),
            "duration_s": float(self.cfg["duration_s"]),
            "dt_s": float(self.cfg["dt_s"]),
            "finished": self.time_s >= float(self.cfg["duration_s"]) - 1e-9,
            "vehicles": vehicles,
            "queues": {
                "mainline": len(self.mainline_queue),
                "ramp": len(self.ramp_queue),
                "ramp_overflow": self.ramp_overflow,
            },
            "metrics": {
                "active_vehicles": len(self.vehicles),
                "exited_vehicles": self.exited,
                "throughput_veh_h": round(self.exited * 3600.0 / elapsed, 2),
                "total_delay_veh_h": round(total_delay / 3600.0, 4),
                "mean_speed_mps": round(mean_speed, 3),
                "minimum_gap_m": round(minimum_gap, 3) if minimum_gap is not None else None,
                "hard_brake_events": self.hard_brake_events,
                "safety_interventions": self.safety_interventions,
                "collision_guard_activations": self.collision_guard_activations,
                "message_attempts": self.message_attempts,
                "message_received": self.message_received,
                "message_fallbacks": self.message_fallbacks,
                "message_success_rate": round(message_success, 4) if message_success is not None else None,
                "meter_rate_vph": round(self.meter.rate_vph, 1),
            },
            "detectors": detector_records,
            "disturbance": {
                "vehicle_id": self.disturbance_vehicle_id,
                "active": (
                    float(self.cfg["disturbance_time_s"]) <= self.time_s
                    < float(self.cfg["disturbance_time_s"]) + float(self.cfg["disturbance_duration_s"])
                ),
                "start_s": float(self.cfg["disturbance_time_s"]),
                "duration_s": float(self.cfg["disturbance_duration_s"]),
            },
            "road": {
                "length_m": float(self.cfg["road_length_m"]),
                "ramp_position_m": float(self.cfg["ramp_position_m"]),
                "vehicle_length_m": length,
            },
        }

    def _finalize(self) -> None:
        if self._finalized:
            return
        self._close_detector_intervals()
        self.unmet_mainline = len(self.mainline_queue)
        self.unmet_ramp = len(self.ramp_queue) + self.ramp_overflow
        self.total_vehicle_delay_s += sum(v.accumulated_delay_s for v in self.vehicles)
        self._finalized = True

    def run(self) -> dict[str, Any]:
        dt = float(self.cfg["dt_s"])
        duration = float(self.cfg["duration_s"])
        while self.time_s < duration - 1e-9:
            self.step()
        self._finalize()
        total_delay = self.total_vehicle_delay_s + self.total_boundary_delay_s
        all_generated = int(self.cfg["initial_platoon_size"]) + self.generated_mainline + self.generated_ramp
        unfinished = len(self.vehicles) + self.unmet_mainline + self.unmet_ramp
        return {
            "scenario_id": self.scenario["scenario_id"],
            "demand_id": self.scenario["demand"],
            "seed": int(self.cfg["seed"]),
            "model_version": "idm-open-freeway-v1.0",
            "controller_version": "cth-pd-feedforward-safety-v1.1",
            "controller": self.scenario["controller"],
            "penetration": float(self.scenario["penetration"]),
            "comm_delay_s": float(self.scenario["comm_delay_s"]),
            "dropout_probability": float(self.scenario["dropout_probability"]),
            "dt_s": dt,
            "generated_vehicles": all_generated,
            "exited_vehicles": self.exited,
            "throughput_veh_h": self.exited * 3600.0 / duration,
            "total_delay_veh_h": total_delay / 3600.0,
            "boundary_delay_veh_h": self.total_boundary_delay_s / 3600.0,
            "unfinished_vehicles": unfinished,
            "residual_mainline_vehicles": len(self.vehicles),
            "residual_ramp_queue_vehicles": len(self.ramp_queue),
            "unmet_mainline_vehicles": len(self.mainline_queue),
            "ramp_overflow_vehicles": self.ramp_overflow,
            "minimum_gap_m": self.global_min_gap_m,
            "overlap_steps": self.overlap_steps,
            "hardest_braking_mps2": self.hardest_braking_mps2,
            "hard_brake_events": self.hard_brake_events,
            "safety_interventions": self.safety_interventions,
            "collision_guard_activations": self.collision_guard_activations,
            "message_attempts": self.message_attempts,
            "message_received": self.message_received,
            "message_fallbacks": self.message_fallbacks,
            "disturbance_vehicle_id": self.disturbance_vehicle_id,
            "disturbance_cohort": ";".join(self.disturbance_cohort),
        }

    def tables(self) -> dict[str, pd.DataFrame]:
        return {
            "trajectories": pd.DataFrame(self.trajectory_rows),
            "observations": pd.DataFrame(self.observation_rows),
            "crossings": pd.DataFrame(self.crossing_rows),
            "control_commands": pd.DataFrame(self.command_rows),
            "decision_trace": pd.DataFrame(self.decision_rows),
            "queues": pd.DataFrame(self.ramp_queue_rows),
        }


def disturbance_amplification(trajectories: pd.DataFrame, metric: dict[str, Any], cfg: dict[str, Any]) -> float:
    if trajectories.empty or not metric.get("disturbance_cohort"):
        return math.nan
    ids = str(metric["disturbance_cohort"]).split(";")
    if len(ids) < 2:
        return math.nan
    t0 = float(cfg["disturbance_time_s"])
    losses = []
    for vid in ids:
        sub = trajectories[trajectories["vehicle_id"] == vid]
        pre = sub[(sub["time_s"] >= max(0.0, t0 - 3.0)) & (sub["time_s"] < t0)]["speed_mps"]
        post = sub[(sub["time_s"] >= t0) & (sub["time_s"] <= t0 + 14.0)]["speed_mps"]
        if pre.empty or post.empty:
            losses.append(math.nan)
        else:
            losses.append(max(0.0, float(pre.mean() - post.min())))
    leader_loss = losses[0]
    follower_losses = [x for x in losses[1:] if np.isfinite(x)]
    if not np.isfinite(leader_loss) or leader_loss <= 1e-9 or not follower_losses:
        return math.nan
    return max(follower_losses) / leader_loss
