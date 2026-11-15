#!/usr/bin/env python3
"""Human drivers only: desired time gap T x ramp demand, six runs x 20 seeds.

Question (Intermediate 1/2): under what desired time gap and ramp demand does the on-ramp merge become congested?
Predictions were recorded before the first runs in deliverables/by_submission/01_intermediate_1/experiment_record.md.
Usage (from this folder):  python run_time_gap_sweep.py
Writes outputs/time_gap_sweep/ (all_seeds.csv, seed_means.csv).
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import sys

import pandas as pd

sys.path.insert(0, "src")
from cavsim.metrics import ROOT, load_config, mean_ci, run_case, share_ci, summarize

OUT = ROOT / "outputs" / "time_gap_sweep"
RUNS = [(1, 0.8, 200.0), (2, 0.8, 700.0), (3, 1.0, 200.0), (4, 1.0, 700.0), (5, 1.2, 200.0), (6, 1.2, 700.0)]
SEEDS = list(range(281, 301))


def one_run(args: tuple) -> dict:
    run, T, ramp, seed = args
    metric, tables, cfg = run_case(load_config(), T=T, ramp=ramp, seed=seed)
    return {"run": run, **summarize(cfg, metric, tables)}


def seed_means(table: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Mean over seeds with 95% confidence intervals."""
    rows = []
    for key, g in table.groupby(keys):
        share, low, high = share_ci(g.congested)
        row = dict(zip(keys, key if isinstance(key, tuple) else (key,)))
        row.update(seeds=len(g), demand_over_capacity_pct=g.demand_over_capacity_pct.iloc[0],
                   congested_share=share, congested_share_low=low, congested_share_high=high)
        for col in ("waiting_at_10min_veh", "total_delay_veh_h", "merge_discharge_vph", "stops_per_queued_vehicle",
                    "wave_speed_kmh", "max_ramp_queue_veh"):
            m, h = mean_ci(g[col] if col not in ("merge_discharge_vph", "stops_per_queued_vehicle", "wave_speed_kmh")
                           else g.loc[g.congested, col])
            row[col], row[col + "_ci"] = m, h
        row.update(overlap_steps=int(g.overlap_steps.sum()), minimum_gap_m=g.minimum_gap_m.min(),
                   conservation_ok=bool(g.conservation_ok.all()))
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(run, T, ramp, seed) for seed in SEEDS for run, T, ramp in RUNS]
    with ProcessPoolExecutor(max_workers=min(len(jobs), 120)) as pool:
        table = pd.DataFrame(list(pool.map(one_run, jobs)))
    table.to_csv(OUT / "all_seeds.csv", index=False)
    means = seed_means(table, ["run", "T_s", "ramp_vph"])
    means.to_csv(OUT / "seed_means.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(table[table.seed == 281][["run", "T_s", "ramp_vph", "demand_over_capacity_pct", "congested", "d1_slow_intervals",
                                    "zone_congested_s", "waiting_at_10min_veh", "merge_discharge_vph",
                                    "stops_per_queued_vehicle", "wave_speed_kmh", "overlap_steps", "minimum_gap_m"]].to_string(index=False))
    print(means.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
