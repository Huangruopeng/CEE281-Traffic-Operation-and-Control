#!/usr/bin/env python3
"""Intermediate 1 minimum case: human drivers, unmetered ramp, one bottleneck, one braking disturbance.

Usage (from this folder):  python run_int1.py
Writes outputs/int1/ (CSV tables, figures, int1_results.json) and prints the numbers that are compared
with the pre-run predictions in deliverables/by_submission/01_intermediate_1/experiment_record.md.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from cavsim.core import FreewaySimulation, disturbance_amplification

SLOW_MPS = 40 / 3.6          # "congested" = slower than 40 km/h
OUT = ROOT / "outputs" / "int1"


def run_case(config: dict, dt: float) -> tuple[dict, dict]:
    sim_cfg = dict(config["simulation"], dt_s=dt, control_update_s=max(dt, 0.1), log_all_vehicles=True)
    scenario = config["int1_scenario"]          # human drivers only, ramp meter off
    meter_cfg = dict(config["ramp_meter"], mode=scenario["meter_mode"])
    sim = FreewaySimulation(sim_cfg, config["human_idm"], config["automated_controller"], meter_cfg, scenario)
    metric = sim.run()
    tables = sim.tables()
    metric["disturbance_amplification"] = disturbance_amplification(tables["trajectories"], metric, sim_cfg)
    return metric, tables


def prediction_checks(config: dict, metric: dict, tables: dict) -> dict:
    s = config["simulation"]
    traj, obs, queues = tables["trajectories"], tables["observations"], tables["queues"]
    late = traj[traj.time_s > 30.0]                       # after the platoon disturbance has passed
    slow = late[late.speed_mps < SLOW_MPS]
    upstream = slow[slow.position_m < s["bottleneck_start_m"]]
    first = slow.sort_values("time_s").iloc[0] if len(slow) else None
    queue_size = upstream.groupby("time_s").size()
    d1 = obs[obs.sensor_id == "D1"].set_index("interval_end_s").mean_speed_mps
    d2 = obs[obs.sensor_id == "D2"].set_index("interval_end_s").mean_speed_mps
    in_queue = late[(late.position_m > s["ramp_position_m"]) & (late.position_m < s["bottleneck_start_m"])
                    & (late.time_s > 300) & (late.time_s < 600)]
    return {
        "P1_amplification_ratio": metric["disturbance_amplification"],
        "P2_first_congestion_x_m": None if first is None else float(first.position_m),
        "P2_first_congestion_t_s": None if first is None else float(first.time_s),
        "P3_D1_below_40kmh_at_s": float(d1[d1 < SLOW_MPS].index.min()) if (d1 < SLOW_MPS).any() else None,
        "P3_D2_min_speed_kmh": float(d2.min() * 3.6),
        "P4_queue_mean_speed_kmh_300_600s": float(in_queue.speed_mps.mean() * 3.6) if len(in_queue) else None,
        "P4_queue_min_speed_kmh_300_600s": float(in_queue.speed_mps.min() * 3.6) if len(in_queue) else None,
        "P5_max_vehicles_queued_upstream": int(queue_size.max()) if len(queue_size) else 0,
        "P5_queue_tail_min_x_m": float(upstream.position_m.min()) if len(upstream) else None,
        "P5_max_ramp_queue_veh": int(queues.ramp_queue_veh.max()),
        "P5_ramp_overflow_veh": int(metric["ramp_overflow_vehicles"]),
        "P6_last_congested_t_s": float(slow.time_s.max()) if len(slow) else None,
        "P6_unfinished_vehicles": int(metric["unfinished_vehicles"]),
        "P7_conservation_ok": metric["generated_vehicles"] == metric["exited_vehicles"] + metric["unfinished_vehicles"],
        "P7_overlap_steps": int(metric["overlap_steps"]),
        "P7_minimum_gap_m": float(metric["minimum_gap_m"]),
        "P7_hardest_braking_mps2": float(metric["hardest_braking_mps2"]),
        "total_delay_veh_h": float(metric["total_delay_veh_h"]),
    }


def plot_evidence(config: dict, tables: dict, checks: dict, cohort_ids: list[str]) -> None:
    s = config["simulation"]
    traj, obs, queues = tables["trajectories"], tables["observations"], tables["queues"]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    sc = ax.scatter(traj.time_s / 60, traj.position_m / 1000, c=traj.speed_mps * 3.6, s=0.4,
                    cmap="RdYlGn", vmin=0, vmax=120, rasterized=True)
    ax.axhspan(s["bottleneck_start_m"] / 1000, s["bottleneck_end_m"] / 1000, color="0.85", zorder=0,
               label=f"bottleneck (T = {s['bottleneck_time_gap_s']} s)")
    ax.axhline(s["ramp_position_m"] / 1000, color="k", lw=0.8, label="on-ramp merge")
    for i, x in enumerate(s["detector_positions_m"]):
        ax.axhline(x / 1000, color="royalblue", ls="--", lw=0.7, label="detectors D1, D2" if i == 0 else None)
    ax.set(xlabel="time [min]", ylabel="position [km] (traffic moves upward)",
           title="Intermediate 1 minimum case: every vehicle, colored by speed")
    ax.legend(loc="lower right", fontsize=8)
    fig.colorbar(sc, ax=ax, label="speed [km/h]")
    fig.tight_layout(); fig.savefig(OUT / "time_space_all_vehicles.png", dpi=150); plt.close(fig)

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    for sid, g in obs.groupby("sensor_id"):
        a1.plot(g.interval_end_s / 60, g.mean_speed_mps * 3.6, marker=".", label=sid)
    a1.axhline(40, color="gray", ls=":", label="40 km/h")
    a1.set(ylabel="30-s mean speed [km/h]", title="Detector speeds and ramp queue"); a1.legend(fontsize=8)
    a2.plot(queues.time_s / 60, queues.ramp_queue_veh, label="ramp queue")
    a2.axhline(config["ramp_meter"]["storage_vehicles"], color="gray", ls=":", label="ramp storage")
    a2.set(xlabel="time [min]", ylabel="vehicles [veh]"); a2.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "detectors_and_ramp_queue.png", dpi=150); plt.close(fig)

    # Braking car first, then its followers in order (cohort ids are stored leader first).
    t0, t1 = s["disturbance_time_s"], s["disturbance_time_s"] + s["disturbance_duration_s"]
    window = traj[traj.time_s.between(5, 30)]
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, vid in enumerate(cohort_ids):
        g = window[window.vehicle_id == vid]
        lowest = g.loc[g.speed_mps.idxmin()]
        style = dict(lw=3, color="black", label="braking car") if i == 0 else \
            dict(lw=1.3, color=plt.cm.viridis(i / len(cohort_ids)), label=f"follower {i}")
        ax.plot(g.time_s, g.speed_mps * 3.6, **style)
        ax.plot(lowest.time_s, lowest.speed_mps * 3.6, "o", color="red", ms=4,
                label="lowest speed of each car" if i == 0 else None)
    ax.axvspan(t0, t1, color="mistyrose", label="braking car brakes")
    ax.set(xlabel="time [s]", ylabel="speed [km/h]",
           title=f"Braking disturbance: largest follower speed drop / braking car's drop = "
                 f"{checks['P1_amplification_ratio']:.2f}")
    ax.legend(fontsize=7, ncol=3, loc="lower right")
    fig.tight_layout(); fig.savefig(OUT / "disturbance_speed_traces.png", dpi=150); plt.close(fig)


def main() -> None:
    config = json.loads((ROOT / "configs" / "scenarios.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    metric, tables = run_case(config, 0.1)
    checks = prediction_checks(config, metric, tables)
    for name, frame in tables.items():
        frame.to_csv(OUT / f"{name}.csv", index=False)
    plot_evidence(config, tables, checks, metric["disturbance_cohort"].split(";"))

    timestep = {}
    for dt in (0.05, 0.1, 0.2):
        m, t = (metric, tables) if dt == 0.1 else run_case(config, dt)
        c = checks if dt == 0.1 else prediction_checks(config, m, t)
        timestep[str(dt)] = {k: c[k] for k in ("P1_amplification_ratio", "total_delay_veh_h",
                                               "P3_D1_below_40kmh_at_s", "P7_overlap_steps", "P7_minimum_gap_m")}
    results = {"dt_0.1": checks, "P8_timestep": timestep}
    (OUT / "int1_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
