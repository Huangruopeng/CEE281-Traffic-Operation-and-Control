# When does an on-ramp merge jam, and do automated vehicles help?

CEE C181/C281 design project, Fall 2026 (CAV pathway). Seunghun Oh and Ruopeng Huang.

A one-lane, 2.5 km freeway with one on-ramp merge at 1.6 km, the only bottleneck. Mainline and ramp vehicles
arrive at random (Poisson) for 10 minutes; each run lasts 15 minutes. Every driver follows the Intelligent
Driver Model (IDM, Treiber and Kesting Table 11.2). Ramp vehicles merge with a MOBIL-type safety check, or by
zipper (taking turns) when traffic is slower than 40 km/h. A ramp meter (fixed rate or ALINEA occupancy
feedback, the basic TMC) can control ramp releases; it is off unless stated. A connected and automated vehicle (CAV) uses the
same IDM but a 0.6 s time gap when the vehicle ahead is also a CAV (cooperative adaptive cruise control); behind
a human driver it keeps the human time gap. Detectors D1 (1,450 m) and D2 (2,050 m) report 30-s counts, mean
speeds and occupancies. **The merge is congested when D1's 30-s mean speed is below 11.1 m/s (40 km/h) for at
least 4 consecutive intervals.**

## Reproduce the results

Python 3.11 with the packages in `requirements.txt`:

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
```

From this folder (each step takes seconds on a many-core machine and a few minutes on a laptop):

| Command | What it produces |
|---|---|
| `python -m unittest discover -s tests` | Unit tests: IDM free motion and equilibrium, CAV gap rule, conservation, detector recount, no collisions |
| `python run_checks.py` | `outputs/checks/checks.csv`: no queue without ramp traffic, detector recount, time-step sensitivity |
| `python run_time_gap_sweep.py` | `outputs/time_gap_sweep/`: human drivers, time gap T = 0.8/1.0/1.2 s x ramp 200/700 veh/h, 20 seeds |
| `python run_cav_sweep.py` | `outputs/cav_sweep/`: CAV share 0-100% at ramp 700 veh/h, human T = 1.0 and 1.2 s, 20 seeds |
| `python run_tmc.py` | `outputs/tmc/`: ramp metering (no meter, fixed 600/900 veh/h, ALINEA 17/15/13%), detector-loss fallback, 0% and 50% CAVs, 20 seeds |
| `python make_report_figures.py` | `outputs/figures/`: the figures of the mid-report (run the three sweeps first) |

`all_seeds.csv` has one row per run; `seed_means.csv` has means over seeds with 95% confidence intervals.

### Where each figure and table of the mid-report comes from

| Report item | Source |
|---|---|
| Fig. 1 (road), Fig. 4 (merge rule) | drawings of the model, no simulation output |
| Fig. 2 (capacity vs. CAV share) | `make_report_figures.py` -> `capacity_vs_cav_share.png` (Eq. 2, no runs needed) |
| Fig. 3 (detector D1) | `make_report_figures.py` -> `detector_d1.png` |
| Fig. 5 (Runs 1-6) | `run_time_gap_sweep.py`, then `make_report_figures.py` -> `six_runs_human.png` |
| Fig. 6 (CAV sweep), Fig. 7 (CAV runs) | `run_cav_sweep.py`, then `make_report_figures.py` -> `cav_sweep_results.png`, `time_space_cav.png` |
| Fig. 8 (ramp metering), Fig. 9 (one TMC run) | `run_tmc.py`, then `make_report_figures.py` -> `tmc_results.png`, `tmc_trace.png` |
| Table 1 (parameters) | `configs/scenarios.json` |
| Table 2 (verification) | `run_checks.py` -> `outputs/checks/checks.csv` |
| Numbers in Sections 3.2-3.4 | `outputs/time_gap_sweep/`, `outputs/cav_sweep/`, `outputs/tmc/` (`seed_means.csv`) |

## Live view

```bash
python run_live.py --port 8781
```

Then open <http://127.0.0.1:8781>. Choose any run (Runs 1-6: time gap x ramp demand), CAV share (0-100%), ramp meter
(none, fixed 600/900 veh/h, ALINEA 17/15/13%, ALINEA 13% with D2 lost at 5 min) and seed (281-300). The side panel shows
the D1 congestion rule and what the TMC observes and decides every 30 s; the charts show D1's 30-s speed, the meter
rate and the vehicles waiting on the mainline and on the ramp.
The live view runs the same `FreewaySimulation.step()` as the batch runs.

## Files

- `configs/scenarios.json`: every parameter value.
- `src/cavsim/core.py`: the simulator (IDM, merge rule and zipper, arrivals, detectors, ramp queue, ramp meter).
- `src/cavsim/metrics.py`: one run with given changes, congestion definition, queue and wave measures, capacity.
- `deliverables/by_submission/`: assignment instructions and records for each submission. The Intermediate 1
  and 2 folders are records made with earlier versions of the model.
