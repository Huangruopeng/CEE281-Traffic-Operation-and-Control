"""Figures for the Intermediate 2 progress presentation. Run from the project folder:
python deliverables/by_submission/02_intermediate_2/presentation/make_figures.py
"""
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
import numpy as np

PROJECT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT))
import run_time_gap_sweep as sweep  # noqa: E402

OUT = Path(__file__).resolve().parent
X_MERGE = 1600.0
plt.rcParams.update({"font.size": 13, "axes.spines.top": False, "axes.spines.right": False})


def capacity_curves() -> None:
    """IDM equilibrium flow-density curves for three time gaps, with the two demand levels."""
    v0, s0, l, delta = 33.33, 2.0, 5.0, 4
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    colors = {0.8: "#4c72b0", 1.0: "#222222", 1.2: "#dd8452"}
    for T, c in colors.items():
        v = np.linspace(0.01, v0 - 0.01, 4000)
        s_e = (s0 + v * T) / np.sqrt(1 - (v / v0) ** delta)
        k = 1000 / (s_e + l)
        q = 3600 * v / (s_e + l)
        ax.plot(k, q, color=c, lw=2.2, label=f"T = {T} s  (C = {q.max():,.0f} veh/h)")
    for d, txt in [(2100, "demand 2,100 veh/h (ramp 200)"), (2600, "demand 2,600 veh/h (ramp 700)")]:
        ax.axhline(d, color="#888888", ls="--", lw=1.2)
        ax.text(118, d + 40, txt, ha="right", fontsize=12, color="#555555",
                bbox=dict(fc="white", ec="none", alpha=0.9, pad=1))
    ax.set(xlabel="density k [veh/km]", ylabel="flow q [veh/h]", xlim=(0, 120), ylim=(0, 3200))
    ax.legend(frameon=False, loc="lower right", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "capacity_curves.png", dpi=170)
    plt.close(fig)


def car(ax, x, y, w=0.9, h=0.5, color="#555555"):
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, color=color, zorder=3))


def merge_rule() -> None:
    """Two panels: gap check in fast traffic, zipper in slow traffic."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 3.8))
    for ax, title in zip(axes, ["Above 40 km/h: gap check (MOBIL safety rule)",
                                "Below 40 km/h: zipper (take turns)"]):
        ax.add_patch(Rectangle((0, -0.45), 14, 0.9, color="#d9d9d9", zorder=1))
        ax.add_patch(Polygon([(5.2, -2.6), (6.3, -2.6), (10.0, -0.45), (8.9, -0.45)], color="#d9d9d9", zorder=1))
        ax.plot([10, 10], [-0.75, 0.75], color="black", lw=2.5, zorder=4)
        ax.text(10, 1.0, "merge point", ha="center", fontsize=12)
        ax.set(xlim=(0, 14), ylim=(-3.0, 1.6), title=title)
        ax.title.set_fontsize(13)
        ax.axis("off")
    a, b = axes
    # fast: large gaps, ramp car enters if the new follower need not brake harder than b_safe
    for x in (2.0, 6.4, 12.6):
        car(a, x, 0)
    car(a, 8.6, -1.2, color="#2b5b84")
    a.annotate("", xy=(9.6, -0.1), xytext=(8.8, -1.0), arrowprops=dict(arrowstyle="->", color="#2b5b84", lw=2))
    a.text(7.0, -2.75, "enter at the leader's speed (max 89 km/h)\nonly if the new follower brakes less than b_safe",
           fontsize=11.5, ha="center", va="top")
    # slow: dense queue; the first car within 100 m stops behind the merge point and leaves one slot
    for x in (0.9, 2.2, 3.5, 4.8, 6.1, 7.4):
        car(b, x, 0)
    car(b, 8.6, 0, color="#dd8452")
    b.text(8.6, 0.55, "yields", ha="center", fontsize=11, color="#b05a1e")
    b.add_patch(Rectangle((9.25, -0.35), 0.75, 0.7, fill=False, ls="--", ec="#2b5b84", lw=1.5, zorder=3))
    car(b, 9.2, -1.25, color="#2b5b84")
    b.annotate("", xy=(9.6, -0.15), xytext=(9.3, -0.95), arrowprops=dict(arrowstyle="->", color="#2b5b84", lw=2))
    for x in (11.3, 12.6):
        car(b, x, 0)
    b.text(7.0, -2.75, "first mainline car within 100 m stops behind the merge point;\n"
           "one ramp car enters, then one mainline car passes, and so on",
           fontsize=11.5, ha="center", va="top")
    fig.tight_layout()
    fig.savefig(OUT / "merge_rule.png", dpi=170)
    plt.close(fig)


def scatter_ts(ax, traj, t_rng=None, x_rng=None, s=0.25):
    t = traj
    if t_rng:
        t = t[t.time_s.between(*t_rng)]
    if x_rng:
        t = t[t.position_m.between(*x_rng)]
    return ax.scatter(t.time_s / 60, t.position_m / 1000, c=t.speed_mps * 3.6, s=s, cmap="RdYlGn",
                      vmin=0, vmax=120, rasterized=True)


def six_runs(rows) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15, 6.6), sharex=True, sharey=True)
    for r in rows:
        ax = axes[[200.0, 700.0].index(r["ramp_vph"]), [0.8, 1.0, 1.2].index(r["T_s"])]
        sc = scatter_ts(ax, r["_traj"])
        ax.axhline(X_MERGE / 1000, color="black", lw=1)
        verdict = "queue" if r["persistent_queue"] else "no queue"
        ax.set_title(f"Run {r['run']}: T = {r['T_s']} s, ramp {r['ramp_vph']:.0f} veh/h\n"
                     f"demand/C = {r['demand_over_capacity_pct']:.0f}%  →  {verdict}", fontsize=12)
    for ax in axes[1]:
        ax.set_xlabel("time [min]")
    for ax in axes[:, 0]:
        ax.set_ylabel("position [km]")
    fig.subplots_adjust(hspace=0.42)
    fig.colorbar(sc, ax=axes, label="speed [km/h]", shrink=0.8, pad=0.01)
    fig.savefig(OUT / "six_runs.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def waves(run4, full) -> None:
    """Zoom on the Run 4 queue with the measured wave speed, plus one vehicle's speed over time."""
    traj = run4["_traj"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(14, 5.4), gridspec_kw={"width_ratios": [1.5, 1]})
    sc = scatter_ts(a, traj, (300, 800), (300, 1700), s=0.6)
    a.axhline(X_MERGE / 1000, color="black", lw=1)
    c = run4["wave_speed_kmh"]  # km/h, negative = backward
    t0, x0 = 9.0, 1.55
    tt = np.array([t0, t0 + 3.0])
    a.plot(tt, x0 + c * (tt - t0) / 60, color="#2b5b84", lw=2.5, ls="--")
    a.annotate(f"wave moves backward\nat {abs(c):.1f} km/h", xy=(t0 + 2.0, x0 + c * 2.0 / 60),
               xytext=(9.5, 0.42), color="#2b5b84", fontsize=13, fontweight="bold",
               arrowprops=dict(arrowstyle="->", color="#2b5b84", lw=1.5))
    a.set(xlabel="time [min]", ylabel="position [km]", title="Run 4 queue (T = 1.0 s, ramp 700): red bands = stops")
    a.title.set_fontsize(13)
    fig.colorbar(sc, ax=a, label="speed [km/h]", pad=0.01)
    # one vehicle that crosses the queue
    ids = full[(full.position_m.between(900, 1000)) & (full.time_s.between(560, 600))].vehicle_id.unique()
    vid = ids[len(ids) // 2]
    d = full[full.vehicle_id == vid].sort_values("time_s")
    b.plot(d.time_s / 60, d.speed_mps * 3.6, color="#222222", lw=1.6)
    b.set(xlabel="time [min]", ylabel="speed [km/h]", title=f"One queued vehicle ({vid}): stop, go, stop ...",
          ylim=(0, 125))
    b.title.set_fontsize(13)
    fig.tight_layout()
    fig.savefig(OUT / "waves.png", dpi=160)
    plt.close(fig)


def breakdown(r_ok, r_bad) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.9), sharey=True)
    for ax, r, label in [(axes[0], r_ok, "seed 281"), (axes[1], r_bad, "seed 284")]:
        sc = scatter_ts(ax, r["_traj"])
        ax.axhline(X_MERGE / 1000, color="black", lw=1)
        verdict = f"queue for {r['longest_congested_s'] / 60:.1f} min" if r["persistent_queue"] else "no queue"
        ax.set_title(f"{label}: {verdict}", fontsize=13)
        ax.set_xlabel("time [min]")
    axes[0].set_ylabel("position [km]")
    fig.suptitle("Run 2: T = 0.8 s, ramp 700 veh/h, demand = 88% of capacity", fontsize=14)
    fig.colorbar(sc, ax=axes, label="speed [km/h]", pad=0.01)
    fig.savefig(OUT / "breakdown_below_capacity.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def idm_equation() -> None:
    fig = plt.figure(figsize=(7.2, 3.2), facecolor="#FAFAF7")
    fig.text(0.02, 0.74, r"$\dfrac{dv}{dt} = a\left[1 - \left(\dfrac{v}{v_0}\right)^{\delta} - \left(\dfrac{s^*}{s}\right)^2\right]$",
             fontsize=26, va="center")
    fig.text(0.02, 0.24, r"$s^* = s_0 + vT + \dfrac{v\,\Delta v}{2\sqrt{ab}}$", fontsize=26, va="center")
    fig.savefig(OUT / "idm_equation.png", dpi=170, facecolor="#FAFAF7", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


if __name__ == "__main__":
    idm_equation()
    capacity_curves()
    merge_rule()
    rows = [sweep.one_run((run, T, ramp, 281, True)) for run, T, ramp in sweep.RUNS]
    six_runs(rows)
    # full trajectories (with vehicle ids) for the single-vehicle speed trace
    import json, copy
    from run_int1 import ROOT, run_case
    cfg = json.loads((ROOT / "configs" / "scenarios.json").read_text(encoding="utf-8"))
    full = run_case(copy.deepcopy(cfg), 0.1)[1]["trajectories"]
    waves(rows[3], full)
    breakdown(rows[1], sweep.one_run((2, 0.8, 700.0, 284, True)))
    print("figures written to", OUT)
