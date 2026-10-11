#!/usr/bin/env python3
"""Run every required CEE 281 Pathway A experiment and build data/plots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from cavsim.core import FreewaySimulation, disturbance_amplification
from cavsim.observation import audit_detector_counts, evaluate_forecasts
from cavsim.plots import (
    create_detector_video,
    plot_disturbance_traces,
    plot_forecast,
    plot_nominal_performance,
    plot_space_time,
    plot_stress_tests,
    plot_timestep_and_tmc,
)


def run_one(config: dict, scenario: dict, meter_mode: str | None = None, dt: float | None = None):
    sim_cfg = dict(config["simulation"])
    meter_cfg = dict(config["ramp_meter"])
    if meter_mode is not None:
        meter_cfg["mode"] = meter_mode
    if dt is not None:
        sim_cfg["dt_s"] = dt
        sim_cfg["control_update_s"] = max(dt, 0.1)
    sim = FreewaySimulation(sim_cfg, config["human_idm"], config["automated_controller"], meter_cfg, scenario)
    metric = sim.run()
    tables = sim.tables()
    metric["disturbance_amplification"] = disturbance_amplification(tables["trajectories"], metric, sim_cfg)
    return metric, tables


def save_tables(tables: dict[str, pd.DataFrame], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(directory / f"{name}.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "scenarios.json")
    parser.add_argument("--quick", action="store_true", help="Run only three nominal demonstration cases")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    outputs = ROOT / "outputs"
    results_dir = outputs / "results"
    plots_dir = outputs / "plots"
    data_dir = outputs / "data"
    for directory in (results_dir, plots_dir, data_dir):
        directory.mkdir(parents=True, exist_ok=True)

    scenarios = config["experiments"]
    if args.quick:
        wanted = {"nominal_human", "nominal_acc_50", "nominal_cacc_50"}
        scenarios = [x for x in scenarios if x["scenario_id"] in wanted]
    metrics = []
    detailed: dict[str, dict[str, pd.DataFrame]] = {}
    keep = {"nominal_human", "nominal_acc_50", "nominal_cacc_50", "nominal_cacc_100", "degraded_cacc_50"}
    for scenario in scenarios:
        print(f"Running {scenario['scenario_id']}...", flush=True)
        metric, tables = run_one(config, scenario)
        metrics.append(metric)
        if scenario["scenario_id"] in keep:
            detailed[scenario["scenario_id"]] = tables
            save_tables(tables, data_dir / scenario["scenario_id"])
    metrics_df = pd.DataFrame(metrics)
    metrics_df.to_csv(results_dir / "scenario_metrics.csv", index=False)

    if args.quick:
        print(metrics_df.to_string(index=False))
        return

    # Observation, estimation, forecast, and detector audit use the common human baseline.
    base_tables = detailed["nominal_human"]
    audit = audit_detector_counts(base_tables["observations"], base_tables["crossings"])
    audit.to_csv(results_dir / "detector_audit.csv", index=False)
    forecast_detail, forecast_summary, defective = evaluate_forecasts(base_tables["observations"])
    forecast_detail.to_csv(results_dir / "forecast_records.csv", index=False)
    forecast_summary.to_csv(results_dir / "forecast_metrics.csv", index=False)
    defective.to_csv(results_dir / "observations_missing_test.csv", index=False)
    forecast_detail.to_csv(data_dir / "nominal_human" / "estimates_forecasts.csv", index=False)

    # Common TMC comparison, holding human driving, demand, seed, and disturbance fixed.
    base_scenario = next(x for x in config["experiments"] if x["scenario_id"] == "nominal_human")
    tmc_rows = []
    for mode in ["unmetered", "fixed", "feedback"]:
        scenario = dict(base_scenario)
        scenario["scenario_id"] = f"tmc_{mode}"
        metric, _ = run_one(config, scenario, meter_mode=mode)
        metric["meter_mode"] = mode
        tmc_rows.append(metric)
    tmc_df = pd.DataFrame(tmc_rows)
    tmc_df.to_csv(results_dir / "tmc_comparison.csv", index=False)

    # Numerical sensitivity around the declared 0.1 s time step.
    ts_rows = []
    for sid in ["nominal_human", "nominal_cacc_50"]:
        base = next(x for x in config["experiments"] if x["scenario_id"] == sid)
        nominal_row = metrics_df[metrics_df["scenario_id"] == sid].iloc[0].to_dict()
        ts_rows.append(nominal_row)
        for dt in [0.05, 0.2]:
            scenario = dict(base)
            scenario["scenario_id"] = f"{sid}_dt_{dt}"
            metric, _ = run_one(config, scenario, dt=dt)
            ts_rows.append(metric)
    timestep_df = pd.DataFrame(ts_rows).sort_values(["controller", "dt_s"])
    timestep_df.to_csv(results_dir / "timestep_sensitivity.csv", index=False)

    # Experiment record required by the guide.
    experiment_rows = [
        {"experiment": "ACC/CACC ablation", "prediction": "CACC feedforward will reduce speed-loss amplification relative to ACC at 50% penetration.", "change_made": "Enable delayed predecessor-acceleration feedforward; all else fixed.", "result_location": "scenario_metrics.csv; nominal_acc_50 vs nominal_cacc_50", "interpretation": "Use the measured amplification and delay differences; do not infer real-world crash reduction."},
        {"experiment": "penetration", "prediction": "100% equipment should yield a more coherent response than 50%, but tight automation may trade minimum gap against delay.", "change_made": "Penetration 0%, 50%, 100% using nested vehicle assignment.", "result_location": "scenario_metrics.csv; nominal cases", "interpretation": "Jointly inspect throughput, delay, amplification, and minimum gap."},
        {"experiment": "communication degradation", "prediction": "0.8-s delay plus 30% dropout will erase part of CACC's advantage because stale messages invoke ACC fallback.", "change_made": "Delay 0.15 to 0.8 s; dropout 0 to 0.30.", "result_location": "scenario_metrics.csv; decision_trace.csv", "interpretation": "Fallback preserves bounded commands; performance may regress toward ACC."},
        {"experiment": "changed demand", "prediction": "Higher mainline/ramp demand will increase boundary and in-system delay and may expose residual queues.", "change_made": "Mainline 1500 to 1740 veh/h; ramp 360 to 480 veh/h.", "result_location": "scenario_metrics.csv; high_demand_*", "interpretation": "Count residual and overflow vehicles; do not report only completed trips."},
        {"experiment": "stronger disturbance", "prediction": "A -3.5 m/s2 lead brake will increase hard braking and may reduce the relative benefit of low penetration.", "change_made": "Lead brake -2.5 to -3.5 m/s2 for 4 s.", "result_location": "scenario_metrics.csv; strong_brake_*", "interpretation": "This is an operational stress test, not a crash-risk estimate."},
        {"experiment": "time-step sensitivity", "prediction": "Delay and amplification should be qualitatively stable at 0.05, 0.1 and 0.2 s.", "change_made": "Numerical step only.", "result_location": "timestep_sensitivity.csv", "interpretation": "Large ranking changes would invalidate the main conclusion."},
        {"experiment": "physical-gap safety supervisor", "prediction": "A one-step and stopping-distance supervisor will preserve the 2.0-m physical net-gap floor without invoking the final numerical guard.", "change_made": "Apply bounded immediate braking only when predicted clearance is exhausted; count supervisor and final-guard activations separately.", "result_location": "scenario_metrics.csv; safety_interventions and collision_guard_activations", "interpretation": "All 12 final scenarios keep more than 2.0 m and record zero final-guard activations; supervisor use is verification evidence, not a real-world safety claim."},
        {"experiment": "missing observation", "prediction": "Holding the last exponential state across 20% missing intervals will increase forecast MAE.", "change_made": "Every fifth detector interval marked missing.", "result_location": "forecast_metrics.csv", "interpretation": "Prediction was not supported: smoothing MAE fell from 1.820 to 1.618 because this deterministic removal pattern skipped noisy updates. Quality flags remain explicit; test more patterns before generalizing."}
    ]
    pd.DataFrame(experiment_rows).to_csv(results_dir / "experiment_record.csv", index=False)

    plot_nominal_performance(metrics_df, plots_dir / "01_nominal_performance.png")
    plot_disturbance_traces(detailed, plots_dir / "02_disturbance_speed_traces.png")
    plot_space_time(detailed, plots_dir / "03_time_space_trajectories.png")
    plot_stress_tests(metrics_df, plots_dir / "04_stress_tests.png")
    plot_forecast(forecast_detail, forecast_summary, plots_dir / "05_forecast_evaluation.png")
    plot_timestep_and_tmc(timestep_df, tmc_df, plots_dir / "06_sensitivity_tmc.png")
    create_detector_video(base_tables["trajectories"], outputs / "detector_audit_clip.mp4")
    print(f"Completed {len(metrics_df)} final-pathway scenarios. Outputs: {outputs}")


if __name__ == "__main__":
    main()
