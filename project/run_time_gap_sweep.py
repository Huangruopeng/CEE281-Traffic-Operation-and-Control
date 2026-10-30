#!/usr/bin/env python3
"""Proposal experiment: desired time gap T x ramp demand (six runs).

Question: under what desired time gap and ramp demand does the on-ramp merge create a persistent mainline queue
with stop-and-go waves? Predictions were recorded before these runs in
deliverables/by_submission/01_intermediate_1/experiment_record.md (Section 10).

Runs 1-6 use seed 281 (the recorded predictions). Seeds 282-285 repeat every run as a robustness check.
Usage (from this folder):  python run_time_gap_sweep.py
Writes outputs/time_gap_sweep/ (runs_seed281.csv, all_seeds.csv, seed_means.csv, time_space_six_runs.png).
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from run_int1 import ROOT, SLOW_MPS, prediction_checks, run_case

OUT = ROOT / "outputs" / "time_gap_sweep"
RUNS = [(1, 0.8, 200.0), (2, 0.8, 700.0), (3, 1.0, 200.0), (4, 1.0, 700.0), (5, 1.2, 200.0), (6, 1.2, 700.0)]
SEEDS = [281, 282, 283, 284, 285]
ZONE_M = 300.0        # "before the merge" = the 300 m upstream of the merge point
PERSISTENT_S = 120.0  # persistent queue = zone mean speed below 40 km/h for more than 2 min in a row


def capacity_vph(cfg: dict, length_m: float, v0: float) -> float:
    """Lane capacity from the IDM equilibrium: max over v of 3600 v / (s_e(v) + l)."""
    v = np.linspace(0.01, v0 - 0.01, 20000)
    s_e = (cfg["minimum_gap_m"] + v * cfg["desired_time_gap_s"]) / np.sqrt(1 - (v / v0) ** cfg["accel_exponent"])
    return float((3600 * v / (s_e + length_m)).max())


def longest_congested_spell(traj: pd.DataFrame, x_merge: float, dt_log: float) -> tuple[float, float, float]:
    """Longest run of log times at which the mean speed in the zone before the merge is below 40 km/h.
    Returns (duration_s, start_s, end_s)."""
    zone = traj[(traj.position_m >= x_merge - ZONE_M) & (traj.position_m < x_merge) & (traj.time_s > 30)]
    speed = zone.groupby("time_s").speed_mps.mean()
    times = np.round(np.arange(0, traj.time_s.max() + dt_log, dt_log), 3)
    slow = speed.reindex(times).lt(SLOW_MPS).to_numpy()     # no vehicle in the zone -> not congested
    best, start, run_start = 0, None, None
    for i, flag in enumerate(slow):
        if flag and run_start is None:
            run_start = i
        if (not flag or i == len(slow) - 1) and run_start is not None:
            end = i if flag else i - 1
            if end - run_start + 1 > best:
                best, start = end - run_start + 1, run_start
            run_start = None
    if best == 0:
        return 0.0, float("nan"), float("nan")
    return best * dt_log, float(times[start]), float(times[start + best - 1])


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


def one_run(args: tuple) -> dict:
    run, T, ramp, seed, keep_traj = args
    config = json.loads((ROOT / "configs" / "scenarios.json").read_text(encoding="utf-8"))
    config = copy.deepcopy(config)
    config["human_idm"]["desired_time_gap_s"] = T
    config["int1_scenario"]["ramp_demand_vph"] = ramp
    config["simulation"]["seed"] = seed
    s = config["simulation"]
    x_merge = s["ramp_position_m"]
    metric, tables = run_case(config, 0.1)
    checks = prediction_checks(config, metric, tables)
    traj, obs, queues = tables["trajectories"], tables["observations"], tables["queues"]
    cap = capacity_vph(config["human_idm"], s["vehicle_length_m"], s["free_speed_mps"])
    demand = config["int1_scenario"]["mainline_demand_vph"] + ramp
    spell, t0, t1 = longest_congested_spell(traj, x_merge, s["log_interval_s"])
    persistent = spell > PERSISTENT_S
    stops, wave = stop_and_go(traj, x_merge, t0, t1) if persistent else (0.0, float("nan"))
    at10 = traj[(traj.time_s == 600.0) & (traj.position_m < x_merge) & (traj.speed_mps < SLOW_MPS)]
    ramp10 = int(queues.loc[queues.time_s == 600.0, "ramp_queue_veh"].iloc[0])
    d2 = obs[(obs.sensor_id == "D2") & (obs.interval_start_s >= t0) & (obs.interval_end_s <= t1)] if persistent else obs.iloc[0:0]
    row = {
        "run": run, "seed": seed, "T_s": T, "ramp_vph": ramp, "demand_vph": demand,
        "capacity_vph": round(cap), "demand_over_capacity_pct": round(100 * demand / cap, 1),
        "persistent_queue": persistent, "longest_congested_s": spell,
        "congested_from_s": t0, "congested_to_s": t1,
        "waiting_at_10min_veh": len(at10) + ramp10, "mainline_queued_at_10min": len(at10), "ramp_queue_at_10min": ramp10,
        "max_mainline_queued_veh": checks["P5_max_vehicles_queued_upstream"],
        "queue_tail_min_x_m": checks["P5_queue_tail_min_x_m"],
        "max_ramp_queue_veh": checks["P5_max_ramp_queue_veh"], "ramp_overflow_veh": checks["P5_ramp_overflow_veh"],
        "merge_discharge_vph": float(d2["count"].mean() * 120) if len(d2) else float("nan"),
        "stops_per_queued_vehicle": stops, "wave_speed_kmh": wave,
        "last_slow_s": checks["P6_last_congested_t_s"], "unfinished_veh": checks["P6_unfinished_vehicles"],
        "conservation_ok": checks["P7_conservation_ok"], "overlap_steps": checks["P7_overlap_steps"],
        "minimum_gap_m": checks["P7_minimum_gap_m"], "hardest_braking_mps2": checks["P7_hardest_braking_mps2"],
        "total_delay_veh_h": checks["total_delay_veh_h"],
    }
    if keep_traj:
        row["_traj"] = traj[["time_s", "position_m", "speed_mps"]]
    return row


def plot_six(rows: list[dict], x_merge: float) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(11, 10), sharex=True, sharey=True)
    for r in rows:
        ax = axes[[0.8, 1.0, 1.2].index(r["T_s"]), [200.0, 700.0].index(r["ramp_vph"])]
        t = r["_traj"]
        sc = ax.scatter(t.time_s / 60, t.position_m / 1000, c=t.speed_mps * 3.6, s=0.2, cmap="RdYlGn",
                        vmin=0, vmax=120, rasterized=True)
        ax.axhline(x_merge / 1000, color="k", lw=1)
        verdict = "persistent queue" if r["persistent_queue"] else "no persistent queue"
        ax.set_title(f"Run {r['run']}: T = {r['T_s']} s, ramp {r['ramp_vph']:.0f} veh/h, "
                     f"demand/C = {r['demand_over_capacity_pct']:.0f}%\n{verdict}", fontsize=9)
    for ax in axes[-1]:
        ax.set_xlabel("time [min]")
    for ax in axes[:, 0]:
        ax.set_ylabel("position [km]")
    fig.colorbar(sc, ax=axes, label="speed [km/h]", shrink=0.6)
    fig.suptitle("Six runs (seed 281): every vehicle colored by speed; black line = merge (the bottleneck)")
    fig.savefig(OUT / "time_space_six_runs.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(run, T, ramp, seed, seed == 281) for seed in SEEDS for run, T, ramp in RUNS]
    with ProcessPoolExecutor(max_workers=len(jobs)) as pool:
        rows = list(pool.map(one_run, jobs))
    main_rows = [r for r in rows if r["seed"] == 281]
    config = json.loads((ROOT / "configs" / "scenarios.json").read_text(encoding="utf-8"))
    plot_six(main_rows, config["simulation"]["ramp_position_m"])
    table = pd.DataFrame([{k: v for k, v in r.items() if k != "_traj"} for r in rows])
    table[table.seed == 281].to_csv(OUT / "runs_seed281.csv", index=False)
    table.to_csv(OUT / "all_seeds.csv", index=False)
    means = table.groupby(["run", "T_s", "ramp_vph", "demand_over_capacity_pct"]).agg(
        persistent_share=("persistent_queue", "mean"), longest_congested_s=("longest_congested_s", "mean"),
        waiting_at_10min_veh=("waiting_at_10min_veh", "mean"), max_mainline_queued_veh=("max_mainline_queued_veh", "mean"),
        max_ramp_queue_veh=("max_ramp_queue_veh", "mean"), merge_discharge_vph=("merge_discharge_vph", "mean"),
        total_delay_veh_h=("total_delay_veh_h", "mean"), overlap_steps=("overlap_steps", "sum")).reset_index()
    means.to_csv(OUT / "seed_means.csv", index=False)
    pd.set_option("display.width", 250)
    print(table[table.seed == 281][["run", "T_s", "ramp_vph", "demand_over_capacity_pct", "persistent_queue",
                                    "longest_congested_s", "waiting_at_10min_veh", "max_mainline_queued_veh",
                                    "queue_tail_min_x_m", "max_ramp_queue_veh", "merge_discharge_vph",
                                    "stops_per_queued_vehicle", "wave_speed_kmh", "last_slow_s",
                                    "overlap_steps", "minimum_gap_m", "unfinished_veh"]].to_string(index=False))
    print(means.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
