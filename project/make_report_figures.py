#!/usr/bin/env python3
"""Figures of the mid-report. Run run_time_gap_sweep.py, run_cav_sweep.py and run_tmc.py first.
Usage (from this folder):  python make_report_figures.py
Writes outputs/figures/*.png.
"""

from __future__ import annotations

import copy
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from cavsim.metrics import ROOT, SLOW_MPS, capacity_vph, load_config, run_case, stop_and_go, summarize

OUT = ROOT / "outputs" / "figures"
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#6b6b6b"     # human T = 1.0 s, human T = 1.2 s, reference lines
COLOR = {1.0: BLUE, 1.2: ORANGE}
plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e6e6e6", "grid.linewidth": 0.6, "savefig.dpi": 200})
CFG = load_config()
S = CFG["simulation"]
X_MERGE = S["ramp_position_m"]
DEMAND = CFG["base_scenario"]["mainline_demand_vph"] + 700.0


def time_space(ax, traj, title, t_lim=(0, 15), x_lim=(0, 2.5), s=0.15):
    sc = ax.scatter(traj.time_s / 60, traj.position_m / 1000, c=traj.speed_mps * 3.6, s=s, cmap="RdYlGn",
                    vmin=0, vmax=120, rasterized=True, linewidths=0)
    ax.axhline(X_MERGE / 1000, color="black", lw=0.8)
    ax.set(xlim=t_lim, ylim=x_lim, title=title)
    ax.grid(False)
    return sc


def capacity_figure() -> None:
    p = np.linspace(0, 1, 101)
    fig, ax = plt.subplots(figsize=(3.4, 2.5))
    for T in (1.0, 1.2):
        idm = dict(CFG["human_idm"], desired_time_gap_s=T)
        c = [capacity_vph(idm, S["vehicle_length_m"], S["free_speed_mps"], x, CFG["cav"]["desired_time_gap_s"]) for x in p]
        ax.plot(100 * p, c, color=COLOR[T], lw=2)
        i = 55 if T == 1.0 else 40           # label each curve where it is clear of the other lines
        ax.text(100 * p[i] + (-3 if T == 1.0 else 3), c[i] + (90 if T == 1.0 else -90), f"human T = {T} s",
                ha="right" if T == 1.0 else "left", va="center", color="#222222", fontsize=8)
    ax.axhline(DEMAND, color=GRAY, ls="--", lw=1)
    ax.text(2, DEMAND + 45, "demand 2,600 veh/h", ha="left", color="#222222", fontsize=8)
    ax.set(xlabel="CAV share p [%]", ylabel="capacity C(p) [veh/h]", xlim=(0, 100), ylim=(2000, 3700))
    fig.tight_layout(); fig.savefig(OUT / "capacity_vs_cav_share.png"); plt.close(fig)


def cav_sweep_figure() -> None:
    m = pd.read_csv(ROOT / "outputs" / "cav_sweep" / "seed_means.csv")
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.4))
    for T, g in m.groupby("T_s"):
        x = 100 * g.penetration
        kw = dict(color=COLOR[T], lw=1.8, marker="o", ms=3.5, label=f"human T = {T} s")
        axes[0].fill_between(x, 100 * g.congested_share_low, 100 * g.congested_share_high, color=COLOR[T], alpha=0.15, lw=0)
        axes[0].plot(x, 100 * g.congested_share, **kw)
        axes[1].fill_between(x, g.waiting_at_10min_veh - g.waiting_at_10min_veh_ci,
                             g.waiting_at_10min_veh + g.waiting_at_10min_veh_ci, color=COLOR[T], alpha=0.15, lw=0)
        axes[1].plot(x, g.waiting_at_10min_veh, **kw)
        ok = g.stops_per_queued_vehicle.notna()
        axes[2].errorbar(x[ok], g.stops_per_queued_vehicle[ok], yerr=g.stops_per_queued_vehicle_ci[ok].fillna(0),
                         capsize=2, elinewidth=0.8, **kw)
    axes[0].set(ylabel="runs congested at D1 [%]", ylim=(-3, 103))
    axes[1].set(ylabel="vehicles waiting at 10 min")
    axes[2].set(ylabel="stops per queued vehicle\n(congested runs only)")
    for ax, letter in zip(axes, "abc"):
        ax.set(xlabel="CAV share p [%]", xlim=(-3, 103))
        ax.set_title(f"({letter})", loc="left", fontsize=9)
    # one legend above the panels, so it covers no curve
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=2, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.92)); fig.savefig(OUT / "cav_sweep_results.png"); plt.close(fig)


def cav_time_space_figure() -> None:
    cases = [(0.0, 281, "p = 0%, seed 281"), (0.5, 281, "p = 50%, seed 281"), (1.0, 281, "p = 100%, seed 281"),
             (1.0, 284, "p = 100%, seed 284")]
    fig, axes = plt.subplots(1, 4, figsize=(7.0, 2.3), sharey=True)
    for ax, (p, seed, title) in zip(axes, cases):
        _, tables, _ = run_case(CFG, penetration=p, seed=seed)
        sc = time_space(ax, tables["trajectories"], title)
        ax.title.set_fontsize(8)
        ax.set_xlabel("time [min]")
    axes[0].set_ylabel("position [km]")
    fig.colorbar(sc, ax=axes, label="speed [km/h]", pad=0.01, fraction=0.03)
    fig.savefig(OUT / "time_space_cav.png", bbox_inches="tight"); plt.close(fig)


def six_runs_figure() -> None:
    runs = [(1, 0.8, 200.0), (3, 1.0, 200.0), (5, 1.2, 200.0), (2, 0.8, 700.0), (4, 1.0, 700.0), (6, 1.2, 700.0)]
    fig, axes = plt.subplots(2, 3, figsize=(7.0, 4.6), sharex=True, sharey=True)
    fig.subplots_adjust(hspace=0.45)
    for ax, (n, T, ramp) in zip(axes.flat, runs):
        metric, tables, cfg = run_case(CFG, T=T, ramp=ramp)
        row = summarize(cfg, metric, tables)
        verdict = "congested" if row["congested"] else "not congested"
        sc = time_space(ax, tables["trajectories"],
                        f"Run {n}: T = {T} s, ramp {ramp:.0f}\n{row['demand_over_capacity_pct']:.0f}% of C, {verdict}")
        ax.title.set_fontsize(8)
    for ax in axes[1]:
        ax.set_xlabel("time [min]")
    for ax in axes[:, 0]:
        ax.set_ylabel("position [km]")
    fig.colorbar(sc, ax=axes, label="speed [km/h]", pad=0.01, fraction=0.03)
    fig.savefig(OUT / "six_runs_human.png", bbox_inches="tight"); plt.close(fig)


def detector_figure() -> None:
    fig, (a, b) = plt.subplots(2, 1, figsize=(3.4, 3.6), sharex=True)
    for p, color, label in ((0.0, BLUE, "Run 4, no CAVs"), (0.5, ORANGE, "Run 4, 50% CAVs")):
        _, tables, _ = run_case(CFG, penetration=p)
        d1 = tables["observations"].query("sensor_id == 'D1'")
        t = d1.interval_end_s / 60
        a.step(t, d1.mean_speed_mps, where="post", color=color, lw=1.4, label=label)
        b.step(t, d1.occupancy_pct, where="post", color=color, lw=1.4, label=label)
    a.axhline(SLOW_MPS, color=GRAY, ls="--", lw=1)
    a.text(14.8, SLOW_MPS + 0.8, "11.1 m/s (40 km/h)", ha="right", fontsize=7)
    a.set(ylabel="D1 30-s mean speed [m/s]", ylim=(0, 36))
    b.set(ylabel="D1 occupancy [%]", xlabel="time [min]", xlim=(0, 15))
    a.legend(fontsize=7, frameon=False, loc="lower left")
    fig.tight_layout(); fig.savefig(OUT / "detector_d1.png"); plt.close(fig)


def waves_figure() -> None:
    metric, tables, cfg = run_case(CFG)
    traj = tables["trajectories"]
    row = summarize(cfg, metric, tables)
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.0, 2.6), gridspec_kw={"width_ratios": [1.5, 1]})
    zoom = traj[traj.time_s.between(300, 800) & traj.position_m.between(300, 1700)]
    sc = time_space(a, zoom, "Run 4 queue (seed 281): dark red = stopped", t_lim=(5, 13.3), x_lim=(0.3, 1.7), s=0.4)
    c = row["wave_speed_kmh"]
    t0, x0 = 9.0, 1.55
    tt = np.array([t0, t0 + 3.0])
    a.plot(tt, x0 + c * (tt - t0) / 60, color="#104281", lw=1.8, ls="--")
    a.text(9.4, 0.45, f"wave moves backward\nat {abs(c):.1f} km/h", color="#104281", fontsize=8)
    a.set(xlabel="time [min]", ylabel="position [km]")
    fig.colorbar(sc, ax=a, label="speed [km/h]", pad=0.01)
    ids = traj[traj.position_m.between(900, 1000) & traj.time_s.between(560, 600)].vehicle_id.unique()
    vid = ids[len(ids) // 2]
    d = traj[traj.vehicle_id == vid].sort_values("time_s")
    b.plot(d.time_s / 60, d.speed_mps * 3.6, color="#222222", lw=1.2)
    b.set(xlabel="time [min]", ylabel="speed [km/h]", ylim=(0, 125), title=f"one queued vehicle ({vid})")
    fig.tight_layout(); fig.savefig(OUT / "waves_run4.png"); plt.close(fig)


def tmc_results_figure() -> None:
    m = pd.read_csv(ROOT / "outputs" / "tmc" / "seed_means.csv")
    order = ["no meter", "fixed 600 veh/h", "fixed 900 veh/h", "ALINEA 17%", "ALINEA 15%", "ALINEA 13%",
             "ALINEA 13%, D2 lost at 5 min"]
    names = ["no\nmeter", "fixed\n600", "fixed\n900", "ALINEA\n17%", "ALINEA\n15%", "ALINEA\n13%", "13%,\nD2 lost"]
    names = [n.replace("ALINEA\n", "A ") for n in names]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.6))
    for k, (p, color, label) in enumerate(((0.0, BLUE, "no CAVs"), (0.5, ORANGE, "50% CAVs"))):
        g = m[m.penetration == p].set_index("controller").reindex(order).dropna(subset=["congested_share"])
        x = np.array([order.index(c) for c in g.index]) + (k - 0.5) * 0.18
        axes[0].errorbar(x, 100 * g.congested_share, yerr=[100 * (g.congested_share - g.congested_share_low).clip(lower=0),
                         100 * (g.congested_share_high - g.congested_share)], fmt="o", color=color, ms=4, capsize=2,
                         elinewidth=0.8, label=label)
        axes[1].errorbar(x, g.total_delay_veh_h, yerr=g.total_delay_veh_h_ci, fmt="o", color=color, ms=4, capsize=2,
                         elinewidth=0.8, label=label)
        for xi, (_, r) in zip(x, g.iterrows()):
            if r.ramp_overflow_veh >= 0.5:
                axes[1].text(xi, r.total_delay_veh_h + r.total_delay_veh_h_ci + 0.4, f"{r.ramp_overflow_veh:.0f}",
                             ha="center", fontsize=6.5, color="#222222")
    for ax in axes:
        ax.set_xticks(range(len(order)), names, fontsize=7)
        ax.grid(axis="x", visible=False)
    axes[0].set(ylabel="runs congested at D1 [%]", ylim=(-3, 103))
    axes[1].set(ylabel="total delay [veh$\\cdot$h]", ylim=(0, 15))
    axes[0].legend(fontsize=7, frameon=False, loc="upper right")
    for ax, letter in zip(axes, "ab"):
        ax.set_title(f"({letter})", loc="left", fontsize=9)
    fig.tight_layout(); fig.savefig(OUT / "tmc_results.png"); plt.close(fig)


def tmc_trace_figure() -> None:
    fig, axes = plt.subplots(3, 1, figsize=(3.4, 4.2), sharex=True)
    config = copy.deepcopy(CFG)
    config["ramp_meter"]["target_occupancy_pct"] = 13.0
    for failure, color, label in ((None, BLUE, "ALINEA 13%"), (300.0, ORANGE, "ALINEA 13%, D2 lost at 5 min")):
        _, tables, cfg = run_case(config, meter_mode="alinea", detector_failure_s=failure)
        meter, queues = tables["meter"], tables["queues"]
        if failure is None:
            axes[0].step(meter.time_s / 60, meter.observed_occupancy_pct, where="post", color=color, lw=1.3)
        axes[1].step(meter.time_s / 60, meter.rate_vph, where="post", color=color, lw=1.3)
        axes[2].plot(queues.time_s / 60, queues.ramp_queue_veh, color=color, lw=1.2, label=label)
    axes[0].axhline(cfg["ramp_meter"]["target_occupancy_pct"], color=GRAY, ls="--", lw=1)
    axes[0].text(14.8, cfg["ramp_meter"]["target_occupancy_pct"] + 1, "target 13%", ha="right", fontsize=7)
    axes[2].axhline(cfg["ramp_meter"]["storage_vehicles"], color=GRAY, ls="--", lw=1)
    axes[2].text(14.8, cfg["ramp_meter"]["storage_vehicles"] - 4.5, "storage 35", ha="right", fontsize=7)
    axes[0].set(ylabel="D2 occupancy [%]", ylim=(0, 30))
    axes[1].set(ylabel="release rate\n[veh/h]", ylim=(150, 1000))
    axes[2].set(ylabel="ramp queue [veh]", xlabel="time [min]", xlim=(0, 15), ylim=(0, 40))
    axes[2].legend(fontsize=6.5, frameon=False, loc="upper left")
    fig.tight_layout(); fig.savefig(OUT / "tmc_trace.png"); plt.close(fig)


def breakdown_figure() -> None:
    """Run 2 (88% of capacity): no breakdown with seed 281, breakdown with seed 284 (used in the slides)."""
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8), sharey=True)
    for ax, seed in zip(axes, (281, 284)):
        metric, tables, cfg = run_case(CFG, T=0.8, ramp=700.0, seed=seed)
        row = summarize(cfg, metric, tables)
        verdict = f"congested for {(row['congested_to_s'] - row['congested_from_s']) / 60:.1f} min" if row["congested"] else "not congested"
        sc = time_space(ax, tables["trajectories"], f"seed {seed}: {verdict}")
        ax.set_xlabel("time [min]")
    axes[0].set_ylabel("position [km]")
    fig.colorbar(sc, ax=axes, label="speed [km/h]", pad=0.01, fraction=0.03)
    fig.savefig(OUT / "breakdown_run2.png", bbox_inches="tight"); plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    capacity_figure()
    cav_sweep_figure()
    cav_time_space_figure()
    six_runs_figure()
    detector_figure()
    waves_figure()
    tmc_results_figure()
    tmc_trace_figure()
    breakdown_figure()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
