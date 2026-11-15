"""Run one case and measure it: detector-based congestion, queues, stop-and-go waves, safety checks, and the
IDM equilibrium capacity of mixed human/CAV traffic."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from cavsim.core import FreewaySimulation

ROOT = Path(__file__).resolve().parents[2]
SLOW_MPS = 40 / 3.6          # congested = slower than 40 km/h
CONGESTED_INTERVALS = 4      # congestion at D1 = at least 4 consecutive slow 30-s intervals (2 min)
ZONE_M = 300.0               # trajectory check: the 300 m upstream of the merge


def load_config() -> dict:
    return json.loads((ROOT / "configs" / "scenarios.json").read_text(encoding="utf-8"))


def run_case(config: dict, *, T: float | None = None, ramp: float | None = None, penetration: float | None = None,
             seed: int | None = None, meter_mode: str | None = None, dt: float | None = None) -> tuple[dict, dict, dict]:
    """One simulation of the base scenario with the given changes. Returns (metric, tables, config used)."""
    cfg = copy.deepcopy(config)
    scenario = cfg["base_scenario"]
    if T is not None:
        cfg["human_idm"]["desired_time_gap_s"] = T
    if ramp is not None:
        scenario["ramp_demand_vph"] = ramp
    if penetration is not None:
        scenario["penetration"] = penetration
    if seed is not None:
        cfg["simulation"]["seed"] = seed
    if meter_mode is not None:
        scenario["meter_mode"] = meter_mode
    if dt is not None:
        cfg["simulation"]["dt_s"] = dt
    sim = FreewaySimulation(cfg["simulation"], cfg["human_idm"], cfg["cav"], cfg["ramp_meter"], scenario)
    metric = sim.run()
    return metric, sim.tables(), cfg


def equilibrium_spacing_m(v: np.ndarray, idm: dict, length_m: float, v0: float) -> np.ndarray:
    """IDM steady state: s_e(v) = (s0 + v T) / sqrt(1 - (v/v0)^delta), plus the vehicle length."""
    return (idm["minimum_gap_m"] + v * idm["desired_time_gap_s"]) / np.sqrt(1 - (v / v0) ** idm["accel_exponent"]) + length_m


def capacity_vph(idm: dict, length_m: float, v0: float, penetration: float = 0.0, cav_gap_s: float | None = None) -> float:
    """Lane capacity = max over v of 3600 v / (mean spacing). With CAV share p in random order, a fraction p^2 of
    vehicles are CAVs following CAVs and use the CAV time gap; all others use the human time gap."""
    v = np.linspace(0.01, v0 - 0.01, 20000)
    spacing = equilibrium_spacing_m(v, idm, length_m, v0)
    if penetration > 0:
        cav = equilibrium_spacing_m(v, dict(idm, desired_time_gap_s=cav_gap_s), length_m, v0)
        spacing = (1 - penetration ** 2) * spacing + penetration ** 2 * cav
    return float((3600 * v / spacing).max())


def longest_run(flags) -> tuple[int, int | None]:
    """Length and start index of the longest run of True values."""
    best, best_start, start = 0, None, None
    for i, flag in enumerate(list(flags) + [False]):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            if i - start > best:
                best, best_start = i - start, start
            start = None
    return best, best_start


def detector_congestion(obs: pd.DataFrame, sensor: str = "D1") -> dict:
    """Congestion at a detector: mean speed below 40 km/h for at least 4 consecutive 30-s intervals."""
    d = obs[obs.sensor_id == sensor].sort_values("interval_start_s")
    slow = (d.mean_speed_mps < SLOW_MPS).to_numpy()            # an interval with no crossing counts as not slow
    n, start = longest_run(slow)
    starts, ends = d.interval_start_s.to_numpy(), d.interval_end_s.to_numpy()
    return {"congested": n >= CONGESTED_INTERVALS, "slow_intervals": n,
            "from_s": float(starts[start]) if n else float("nan"),
            "to_s": float(ends[start + n - 1]) if n else float("nan")}


def zone_congested_spell_s(traj: pd.DataFrame, x_merge: float, dt_log: float) -> float:
    """Trajectory check of the detector definition: longest time [s] the mean speed in the 300 m before the merge
    stays below 40 km/h."""
    zone = traj[(traj.position_m >= x_merge - ZONE_M) & (traj.position_m < x_merge)]
    speed = zone.groupby("time_s").speed_mps.mean()
    times = np.round(np.arange(0, traj.time_s.max() + dt_log, dt_log), 3)
    n, _ = longest_run(speed.reindex(times).lt(SLOW_MPS).to_numpy())   # no vehicle in the zone -> not congested
    return n * dt_log


def stop_and_go(traj: pd.DataFrame, x_merge: float, t0: float, t1: float) -> tuple[float, float]:
    """Mean number of stops per vehicle in the queue and backward wave speed [km/h] during [t0, t1]."""
    q = traj[traj.position_m.between(x_merge - 1000, x_merge - 20) & traj.time_s.between(t0, t1)]
    q = q.sort_values(["vehicle_id", "time_s"])
    stops, events = [], []
    for _, d in q.groupby("vehicle_id"):
        v = d.speed_mps.to_numpy() * 3.6
        if len(v) < 20 or v.min() > 5:
            continue
        n, moving = 0, True
        for s in v:                       # a stop = below 3 km/h after having moved faster than 12 km/h
            if moving and s < 3:
                n, moving = n + 1, False
            elif not moving and s > 12:
                moving = True
        stops.append(n)
        flag = (v < 3.6).astype(int)      # stop episodes (below 1 m/s) for the wave speed
        edges = np.flatnonzero(np.diff(np.r_[0, flag, 0]))
        for a, b in zip(edges[::2], edges[1::2]):
            m = (a + b - 1) // 2
            events.append((d.time_s.to_numpy()[m], d.position_m.to_numpy()[m]))
    mean_stops = float(np.mean(stops)) if stops else 0.0
    if len(events) < 30:
        return mean_stops, float("nan")
    ev = np.array(events)
    best = None
    for c_kmh in np.arange(-40, -4, 0.5):  # stops on one wave share t - x / c
        tau = ev[:, 0] - ev[:, 1] / (c_kmh / 3.6)
        h, _ = np.histogram(tau, bins=np.arange(tau.min(), tau.max() + 4, 4))
        score = (h ** 2).sum()
        if best is None or score > best[0]:
            best = (score, c_kmh)
    return mean_stops, float(best[1])


def count_error_veh(obs: pd.DataFrame, crossings: pd.DataFrame) -> int:
    """Largest difference between a detector's interval count and an independent recount of single crossings."""
    worst = 0
    for _, row in obs.iterrows():
        c = crossings[(crossings.sensor_id == row.sensor_id) & (crossings.time_s > row.interval_start_s + 1e-9)
                      & (crossings.time_s <= row.interval_end_s + 1e-9)]
        worst = max(worst, abs(len(c) - int(row["count"])))
    return worst


def summarize(cfg: dict, metric: dict, tables: dict) -> dict:
    """One row of results for a run."""
    s, scenario = cfg["simulation"], cfg["base_scenario"]
    x_merge = s["ramp_position_m"]
    traj, obs, queues = tables["trajectories"], tables["observations"], tables["queues"]
    d1 = detector_congestion(obs, "D1")
    stops, wave = stop_and_go(traj, x_merge, d1["from_s"], d1["to_s"]) if d1["congested"] else (0.0, float("nan"))
    at10 = traj[(traj.time_s == s["demand_end_s"]) & (traj.position_m < x_merge) & (traj.speed_mps < SLOW_MPS)]
    ramp10 = int(queues.loc[queues.time_s == s["demand_end_s"], "ramp_queue_veh"].iloc[0])
    d2 = obs[(obs.sensor_id == "D2") & (obs.interval_start_s >= d1["from_s"]) & (obs.interval_end_s <= d1["to_s"])]
    cap = capacity_vph(cfg["human_idm"], s["vehicle_length_m"], s["free_speed_mps"], scenario["penetration"],
                       cfg["cav"]["desired_time_gap_s"])
    demand = scenario["mainline_demand_vph"] + scenario["ramp_demand_vph"]
    return {
        "seed": s["seed"], "T_s": cfg["human_idm"]["desired_time_gap_s"], "ramp_vph": scenario["ramp_demand_vph"],
        "penetration": scenario["penetration"], "demand_vph": demand, "capacity_vph": round(cap),
        "demand_over_capacity_pct": round(100 * demand / cap, 1),
        "congested": d1["congested"], "d1_slow_intervals": d1["slow_intervals"],
        "congested_from_s": d1["from_s"], "congested_to_s": d1["to_s"],
        "zone_congested_s": zone_congested_spell_s(traj, x_merge, s["log_interval_s"]),
        "waiting_at_10min_veh": len(at10) + ramp10, "mainline_queued_at_10min": len(at10), "ramp_queue_at_10min": ramp10,
        "max_ramp_queue_veh": int(queues.ramp_queue_veh.max()), "ramp_overflow_veh": metric["ramp_overflow_vehicles"],
        "merge_discharge_vph": float(d2["count"].mean() * 3600 / s["detector_interval_s"]) if len(d2) else float("nan"),
        "stops_per_queued_vehicle": stops, "wave_speed_kmh": wave,
        "total_delay_veh_h": metric["total_delay_veh_h"], "unfinished_veh": metric["unfinished_vehicles"],
        "conservation_ok": metric["generated_vehicles"] == metric["exited_vehicles"] + metric["unfinished_vehicles"],
        "overlap_steps": metric["overlap_steps"], "minimum_gap_m": metric["minimum_gap_m"],
        "hardest_braking_mps2": metric["hardest_braking_mps2"],
    }


T_975 = {4: 2.776, 9: 2.262, 19: 2.093, 29: 2.045}   # Student t, 97.5% quantile, by degrees of freedom


def mean_ci(values) -> tuple[float, float]:
    """Mean and half-width of its 95% confidence interval (Student t) over seeds."""
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return (float(x.mean()) if len(x) else float("nan")), float("nan")
    return float(x.mean()), float(T_975.get(len(x) - 1, 1.96) * x.std(ddof=1) / np.sqrt(len(x)))


def share_ci(flags) -> tuple[float, float, float]:
    """Share of True values and its 95% Wilson interval (low, high)."""
    x = np.asarray(flags, dtype=float)
    n, p, z = len(x), float(x.mean()), 1.96
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return p, float(center - half), float(center + half)
