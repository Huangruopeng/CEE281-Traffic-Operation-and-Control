# Individual contribution record

**Contributor:** Rocair (individual project; replace with the official course name and UID if different)

| Owned component | Code/artifact location | Tests or evidence owned | Conclusion owned |
|---|---|---|---|
| IDM dynamics and open freeway boundaries | `src/cavsim/core.py` | Free-motion/equilibrium unit checks; conservation; time-step sensitivity | The chosen human baseline is numerically stable and dissipates the selected disturbance |
| Arrivals, bottleneck, on-ramp storage and release | `core.py::FreewaySimulation`, `core.py::RampMeter` | residual/overflow accounting; TMC comparison | The feedback loop works but the selected occupancy target does not outperform unmetered/fixed release in nominal demand |
| Detector and observation adapter | `core.py::DetectorAccumulator`, `observation.py` | 10-interval event-log recount; missing-value test; audit video | Count audit error is zero; missing inputs remain explicit |
| Estimation and forecasting | `observation.py::evaluate_forecasts` | development/evaluation split; equal-horizon MAE | Exponential smoothing beats the moving-average baseline in this run; the missingness result is pattern-specific |
| ACC/CACC control and communication | `core.py::automated_command`, `_message_for`, `_compute_commands` | bounded decision trace; ACC ablation; delay/dropout test | Feedforward reduces amplification relative to matched ACC but does not dominate all operational/surrogate indicators |
| Experiment integration and accounting | `run_project.py`, `configs/scenarios.json` | 12 scenarios, high demand, stronger braking, 0.05/0.1/0.2-s steps | Results support revision before adoption, not a crash-reduction claim |
| Reporting and presentation | `deliverables/`, `scripts/` | cross-checked tables/plots against CSV outputs; PDF/PPTX visual QA | The report preserves negative findings and identifies the next falsifying tests |

## Independent design defense

At a representative CACC decision, the controller knows ego speed, radar-like local gap and relative speed, and a delayed acceleration message from the immediate equipped predecessor. It does not know future trajectories, the disturbance schedule, downstream truth, or another vehicle's uncommunicated state. If that message is missing, stale, or comes from a human predecessor, the feedforward input becomes zero and the local ACC law remains bounded.

The most useful next test is a constrained gain/headway sweep that rejects any candidate with more hard-braking events than the human baseline. A result showing no feasible candidate improves delay without worsening the braking constraint would overturn the present adoption case.

