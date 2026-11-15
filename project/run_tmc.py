#!/usr/bin/env python3
"""Basic TMC: ramp metering at the merge, Run 4 demand, 20 seeds each. No meter vs. fixed rate (600 or 900 veh/h)
vs. ALINEA (target occupancy 17, 15 or 13%), with 0% and 50% CAVs, plus a degraded-information test (detector D2
lost from 5 min on: the meter falls back to the fixed rate).
Usage (from this folder):  python run_tmc.py
Writes outputs/tmc/ (all_seeds.csv, seed_means.csv, alinea13_trace_seed281.csv).
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import sys

import pandas as pd

sys.path.insert(0, "src")
from cavsim.metrics import ROOT, load_config, mean_ci, run_case, share_ci, summarize
from run_time_gap_sweep import SEEDS

OUT = ROOT / "outputs" / "tmc"
CASES = [  # (label, meter mode, fixed rate [veh/h], ALINEA target occupancy [%], CAV share, D2 lost from [s])
    ("no meter", "unmetered", 600.0, 17.0, 0.0, None), ("fixed 600 veh/h", "fixed", 600.0, 17.0, 0.0, None),
    ("fixed 900 veh/h", "fixed", 900.0, 17.0, 0.0, None), ("ALINEA 17%", "alinea", 600.0, 17.0, 0.0, None),
    ("ALINEA 15%", "alinea", 600.0, 15.0, 0.0, None), ("ALINEA 13%", "alinea", 600.0, 13.0, 0.0, None),
    ("ALINEA 13%, D2 lost at 5 min", "alinea", 600.0, 13.0, 0.0, 300.0),
    ("no meter", "unmetered", 600.0, 17.0, 0.5, None), ("fixed 600 veh/h", "fixed", 600.0, 17.0, 0.5, None),
    ("fixed 900 veh/h", "fixed", 900.0, 17.0, 0.5, None), ("ALINEA 17%", "alinea", 600.0, 17.0, 0.5, None),
    ("ALINEA 15%", "alinea", 600.0, 15.0, 0.5, None), ("ALINEA 13%", "alinea", 600.0, 13.0, 0.5, None),
]


def one_run(args: tuple) -> dict:
    label, mode, rate, target, p, failure, seed = args
    config = load_config()
    config["ramp_meter"].update(fixed_rate_vph=rate, target_occupancy_pct=target)
    metric, tables, cfg = run_case(config, penetration=p, seed=seed, meter_mode=mode, detector_failure_s=failure)
    return {"controller": label, **summarize(cfg, metric, tables)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(*case, seed) for case in CASES for seed in SEEDS]
    with ProcessPoolExecutor(max_workers=min(len(jobs), 140)) as pool:
        table = pd.DataFrame(list(pool.map(one_run, jobs)))
    table.to_csv(OUT / "all_seeds.csv", index=False)
    rows = []
    for (label, p), g in table.groupby(["controller", "penetration"], sort=False):
        share, low, high = share_ci(g.congested)
        row = {"controller": label, "penetration": p, "congested_share": share, "congested_share_low": low,
               "congested_share_high": high}
        for col in ("total_delay_veh_h", "boundary_delay_veh_h", "waiting_at_10min_veh", "max_ramp_queue_veh",
                    "ramp_overflow_veh"):
            row[col], row[col + "_ci"] = mean_ci(g[col])
        row.update(overlap_steps=int(g.overlap_steps.sum()), conservation_ok=bool(g.conservation_ok.all()))
        rows.append(row)
    means = pd.DataFrame(rows)
    means.to_csv(OUT / "seed_means.csv", index=False)
    # decision trace of one run: what the meter saw and did every 30 s
    config = load_config()
    config["ramp_meter"]["target_occupancy_pct"] = 13.0
    _, tables, _ = run_case(config, meter_mode="alinea")
    tables["meter"].to_csv(OUT / "alinea13_trace_seed281.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(means.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
