#!/usr/bin/env python3
"""Verification checks: no queue without ramp traffic, detector counts vs. a recount of single crossings,
vehicle conservation, collisions, and time-step sensitivity (dt = 0.05, 0.1, 0.2 s). Seed 281.
Usage (from this folder):  python run_checks.py
Writes outputs/checks/checks.csv.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import sys

import pandas as pd

sys.path.insert(0, "src")
from cavsim.metrics import ROOT, count_error_veh, load_config, run_case, summarize

OUT = ROOT / "outputs" / "checks"
CASES = [  # (check, ramp demand, CAV share, dt)
    ("no ramp traffic", 0.0, 0.0, 0.1),
    ("base (Run 4)", 700.0, 0.0, 0.1), ("base, dt 0.05 s", 700.0, 0.0, 0.05), ("base, dt 0.2 s", 700.0, 0.0, 0.2),
    ("50% CAV", 700.0, 0.5, 0.1), ("50% CAV, dt 0.05 s", 700.0, 0.5, 0.05), ("50% CAV, dt 0.2 s", 700.0, 0.5, 0.2),
]


def one_check(case: tuple) -> dict:
    name, ramp, p, dt = case
    metric, tables, cfg = run_case(load_config(), ramp=ramp, penetration=p, dt=dt)
    row = summarize(cfg, metric, tables)
    return {"check": name, "dt_s": dt, "detector_count_error_veh": count_error_veh(tables["observations"], tables["crossings"]),
            **{k: row[k] for k in ("penetration", "ramp_vph", "congested", "d1_slow_intervals", "waiting_at_10min_veh",
                                   "total_delay_veh_h", "conservation_ok", "overlap_steps", "minimum_gap_m")}}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=len(CASES)) as pool:
        table = pd.DataFrame(list(pool.map(one_check, CASES)))
    table.to_csv(OUT / "checks.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 20)
    print(table.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
