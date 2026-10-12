# Requirement-to-artifact checklist

For stage-by-stage packaging and oral-preparation guidance, begin at [`by_submission/README.md`](by_submission/README.md). For concept explanations written for a student with no traffic-engineering background, use [`traffic_engineering_primer.md`](traffic_engineering_primer.md).

| Guide requirement | Status | Evidence |
|---|---:|---|
| Runnable freeway simulation with arrivals, exits, bottleneck, ramp queue, detectors | Complete | `src/cavsim/core.py`, `configs/scenarios.json` |
| Model equations, units, parameters, sources, limitations | Complete | `final_report.pdf`, `source_to_design_table.md` |
| Conservation, free/equilibrium motion, >=2.0-m physical gaps, zero final-guard activations, boundaries, time-step, detector audit | Complete | `tests/`, `scenario_metrics.csv`, `timestep_sensitivity.csv`, `detector_audit.csv` |
| Behavioral trajectory and aggregate plots; independent comparison | Complete | plots 01-04, analytical equilibrium, literature trace |
| CEE281 independent comparison/validation evidence | Complete | ACC-vs-CACC ablation and numerical sensitivity; no unsupported validation claim |
| Observation, estimate, 30/60-s forecast, baseline, held-out evaluation | Complete | `observation.py`, forecast CSVs and plot 05 |
| Observation defect | Complete | every-fifth-interval missing test with explicit quality flags |
| Short video exercise | Complete | `outputs/detector_audit_clip.mp4` |
| Optional real-time model demonstration | Complete | `run_live.py`, `live_visualization/`, `start_visualization.sh` |
| Common closed-loop TMC and baseline/sophisticated comparison | Complete | `control_commands.csv`, `tmc_comparison.csv`, plot 06 |
| CAV vehicle-level control law, inputs, update, bounds, response, fallback | Complete | report, interfaces, decision trace, controller code |
| Human and equipped vehicles; declared penetration | Complete | 0/50/100% scenarios |
| No future truth in controller | Complete | interface/code audit; truth only in postprocessing |
| Cooperative ACC plus noncooperative ACC ablation | Complete | nominal ACC/CACC 50/100% |
| Delay/dropout condition | Complete | 0.8-s delay + 30% dropout |
| Changed demand and stronger disturbance | Complete | high-demand and -3.5 m/s2 scenarios |
| Throughput, total delay, trajectories, amplification, gaps/braking | Complete | scenario metrics and plots |
| Residual queues/unmet demand included | Complete | evaluation record columns; high-demand overflow retained |
| README with one command, dependencies, inputs/outputs, limitations | Complete | `README.md`, `run_all.sh`, `requirements.txt` |
| Experiment record | Complete | `outputs/results/experiment_record.csv` |
| Source-to-design table and AI disclosure | Complete | `deliverables/` |
| Named individual contribution record | Provisional | `Ruopeng` used; add the official UID before submission |
| Six-page final design record plus references/plots/code | Complete | `final_report.pdf` (six main pages plus references/traceability) |
| Final presentation: baseline/control, mechanism, failure, adoption defense | Complete | `final_presentation.pdf`, `presentation_source.md`, `presentation_script.md` |

Before submission: confirm the official student name/UID and any instructor-specific file-naming convention not present in the supplied guide.
