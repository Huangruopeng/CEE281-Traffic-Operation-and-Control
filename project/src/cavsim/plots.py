"""Reproducible plots and a short detector-audit video."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter
import numpy as np
import pandas as pd


COLORS = {"human": "#555555", "acc": "#E17C05", "cacc": "#1874CD"}


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_nominal_performance(metrics: pd.DataFrame, path: Path) -> None:
    ids = ["nominal_human", "nominal_acc_50", "nominal_acc_100", "nominal_cacc_50", "nominal_cacc_100", "degraded_cacc_50"]
    sub = metrics.set_index("scenario_id").loc[ids].reset_index()
    labels = ["Human\n0%", "ACC\n50%", "ACC\n100%", "CACC\n50%", "CACC\n100%", "CACC 50%\ndegraded"]
    cs = [COLORS.get(x, "#777777") for x in sub["controller"]]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.2))
    items = [
        ("total_delay_veh_h", "Total delay (veh-h)"),
        ("throughput_veh_h", "Throughput (veh/h)"),
        ("disturbance_amplification", "Disturbance amplification (-)"),
        ("minimum_gap_m", "Minimum simulated gap (m)"),
    ]
    for ax, (col, ylabel) in zip(axes.ravel(), items):
        ax.bar(np.arange(len(sub)), sub[col], color=cs)
        ax.set_xticks(np.arange(len(sub)), labels, fontsize=8)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle("Nominal control comparison and communication degradation", fontweight="bold")
    fig.tight_layout()
    _save(fig, path)


def plot_disturbance_traces(tables: dict[str, dict[str, pd.DataFrame]], path: Path) -> None:
    scenarios = [("nominal_human", "Human baseline"), ("nominal_acc_50", "ACC, 50%"), ("nominal_cacc_50", "CACC, 50%")]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.6), sharey=True)
    for ax, (sid, title) in zip(axes, scenarios):
        df = tables[sid]["trajectories"]
        cohort = df[df["is_disturbance_cohort"] == True]
        for vid, group in cohort.groupby("vehicle_id"):
            ax.plot(group["time_s"], group["speed_mps"], lw=1.1, alpha=0.85)
        ax.axvspan(8.0, 12.0, color="#D62728", alpha=0.12, label="forced brake")
        ax.set_xlim(4, 24)
        ax.set_title(title)
        ax.set_xlabel("Time (s)")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Speed (m/s)")
    axes[0].legend(loc="lower left", fontsize=8)
    fig.suptitle("Lead-braking disturbance response: identical initial platoon", fontweight="bold")
    fig.tight_layout()
    _save(fig, path)


def plot_space_time(tables: dict[str, dict[str, pd.DataFrame]], path: Path) -> None:
    scenarios = [("nominal_human", "Human"), ("nominal_acc_50", "ACC 50%"), ("nominal_cacc_50", "CACC 50%")]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8), sharex=True, sharey=True)
    for ax, (sid, title) in zip(axes, scenarios):
        df = tables[sid]["trajectories"]
        cohort = df[df["is_disturbance_cohort"] == True]
        for _, g in cohort.groupby("vehicle_id"):
            ax.plot(g["time_s"], g["position_m"], lw=1.0)
        ax.set_title(title)
        ax.set_xlabel("Time (s)")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Position (m)")
    fig.suptitle("Time-space trajectories of the disturbance cohort", fontweight="bold")
    fig.tight_layout()
    _save(fig, path)


def plot_stress_tests(metrics: pd.DataFrame, path: Path) -> None:
    groups = [
        ("High demand", ["high_demand_human", "high_demand_acc_50", "high_demand_cacc_50"]),
        ("Stronger braking", ["strong_brake_human", "strong_brake_acc_50", "strong_brake_cacc_50"]),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for row, (name, ids) in enumerate(groups):
        sub = metrics.set_index("scenario_id").loc[ids].reset_index()
        labels = ["Human", "ACC 50%", "CACC 50%"]
        colors = [COLORS[c] for c in sub["controller"]]
        axes[row, 0].bar(labels, sub["total_delay_veh_h"], color=colors)
        axes[row, 0].set_ylabel("Total delay (veh-h)")
        axes[row, 1].bar(labels, sub["disturbance_amplification"], color=colors)
        axes[row, 1].set_ylabel("Amplification (-)")
        axes[row, 0].set_title(name)
        axes[row, 1].set_title(name)
        for ax in axes[row]: ax.grid(axis="y", alpha=0.25)
    fig.suptitle("Changed-demand and stronger-disturbance tests", fontweight="bold")
    fig.tight_layout()
    _save(fig, path)


def plot_forecast(details: pd.DataFrame, summary: pd.DataFrame, path: Path) -> None:
    complete = details[(details["observation_condition"] == "complete") & (details["method"] == "exponential_smoothing")]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8))
    axes[0].plot(complete["target_time_s"], complete["actual_withheld_truth"], marker="o", ms=3, label="withheld truth")
    axes[0].plot(complete["target_time_s"], complete["predicted_value"], marker="s", ms=3, label="exp. smoothing")
    axes[0].axvline(450, color="#555", ls="--", lw=1, label="evaluation begins")
    axes[0].set_xlabel("Target time (s)")
    axes[0].set_ylabel("30-s count (vehicles)")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.25)
    x = np.arange(len(summary))
    width = 0.36
    axes[1].bar(x - width/2, summary["moving_average_3_mae_veh_per_interval"], width, label="moving average")
    axes[1].bar(x + width/2, summary["exponential_smoothing_mae_veh_per_interval"], width, label="exp. smoothing")
    axes[1].set_xticks(x, ["Complete", "20% missing"])
    axes[1].set_ylabel("Evaluation MAE (vehicles/30 s)")
    axes[1].legend(fontsize=8)
    axes[1].grid(axis="y", alpha=0.25)
    fig.suptitle("One-interval flow forecast and missing-observation test", fontweight="bold")
    fig.tight_layout()
    _save(fig, path)


def plot_timestep_and_tmc(timestep: pd.DataFrame, tmc: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8))
    for controller, g in timestep.groupby("controller"):
        axes[0].plot(g["dt_s"], g["total_delay_veh_h"], marker="o", label=controller.upper())
    axes[0].set_xlabel("Simulation time step (s)")
    axes[0].set_ylabel("Total delay (veh-h)")
    axes[0].legend()
    axes[0].grid(alpha=0.25)
    colors = ["#888888", "#E17C05", "#1874CD"]
    axes[1].bar(tmc["meter_mode"], tmc["total_delay_veh_h"], color=colors)
    axes[1].set_xlabel("Ramp-release strategy")
    axes[1].set_ylabel("Total delay (veh-h)")
    axes[1].grid(axis="y", alpha=0.25)
    fig.suptitle("Numerical sensitivity and common TMC foundation", fontweight="bold")
    fig.tight_layout()
    _save(fig, path)


def create_detector_video(trajectories: pd.DataFrame, output: Path, detector_x: float = 1450.0) -> None:
    """Create a short MP4 for manual crossing-count review."""
    df = trajectories[(trajectories["time_s"] >= 35.0) & (trajectories["time_s"] <= 55.0)].copy()
    if df.empty:
        df = trajectories[(trajectories["time_s"] >= 0.0) & (trajectories["time_s"] <= 20.0)].copy()
    times = sorted(df["time_s"].unique())
    fig, ax = plt.subplots(figsize=(9, 2.4))
    scat = ax.scatter([], [], s=55, c="#1874CD")
    label = ax.text(0.02, 0.86, "", transform=ax.transAxes)
    ax.axvline(detector_x, color="#D62728", lw=2, label="D1 detector")
    ax.set_xlim(max(0, detector_x - 500), detector_x + 250)
    ax.set_ylim(-0.5, 0.5)
    ax.set_yticks([])
    ax.set_xlabel("Position (m)")
    ax.legend(loc="lower right")
    ax.set_title("Virtual detector audit clip")

    def update(frame: int):
        t = times[frame]
        pos = df[df["time_s"] == t]["position_m"].to_numpy()
        scat.set_offsets(np.column_stack((pos, np.zeros_like(pos))) if len(pos) else np.empty((0, 2)))
        label.set_text(f"t = {t:.1f} s")
        return scat, label

    ani = FuncAnimation(fig, update, frames=len(times), interval=100, blit=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    ani.save(output, writer=FFMpegWriter(fps=10, codec="libx264", bitrate=1200))
    plt.close(fig)

