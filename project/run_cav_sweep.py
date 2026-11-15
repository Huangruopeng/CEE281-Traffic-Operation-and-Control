#!/usr/bin/env python3
"""CAV share sweep at the merge: CAV share p = 0, 0.1, ..., 1 x two human time gaps, 20 seeds each.

Question: at the demand of Run 4 (1,900 + 700 veh/h, 103% of the human capacity), how large a CAV share is needed
so that the merge is no longer congested, and are the stop-and-go waves weaker when it still is?
Predictions were recorded before running in deliverables/by_submission/03_mid_report/experiment_record.md (Section 2).
Usage (from this folder):  python run_cav_sweep.py
Writes outputs/cav_sweep/ (all_seeds.csv, seed_means.csv).
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import sys

import pandas as pd

sys.path.insert(0, "src")
from cavsim.metrics import ROOT, load_config, run_case, summarize
from run_time_gap_sweep import SEEDS, seed_means

OUT = ROOT / "outputs" / "cav_sweep"
HUMAN_T = [1.0, 1.2]                       # Run 4 and Run 6 demand (ramp 700 veh/h)
SHARES = [round(0.1 * i, 1) for i in range(11)]


def one_run(args: tuple) -> dict:
    T, p, seed = args
    metric, tables, cfg = run_case(load_config(), T=T, ramp=700.0, penetration=p, seed=seed)
    return summarize(cfg, metric, tables)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(T, p, seed) for T in HUMAN_T for p in SHARES for seed in SEEDS]
    with ProcessPoolExecutor(max_workers=min(len(jobs), 200)) as pool:
        table = pd.DataFrame(list(pool.map(one_run, jobs)))
    table.to_csv(OUT / "all_seeds.csv", index=False)
    means = seed_means(table, ["T_s", "penetration"])
    means.to_csv(OUT / "seed_means.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(means.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
