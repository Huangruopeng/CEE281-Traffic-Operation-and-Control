# Intermediate 2 - verified simulation and behavioral evidence

**Guide timing:** after October 28.  
**Purpose:** demonstrate that the freeway, boundaries, detector outputs, and behavioral conclusions survive checks. Confirm a preliminary CAV pathway with initial sources and bounded scope.

## Submit or show

- [`../../design_record.md`](../../design_record.md), through **Intermediate 2**.
- [`../../../src/cavsim/core.py`](../../../src/cavsim/core.py) and [`../../../configs/scenarios.json`](../../../configs/scenarios.json): 2.5-km freeway, arrivals/exits, ramp queue, bottleneck, disturbance, and detectors.
- [`../../../tests/test_project.py`](../../../tests/test_project.py): free motion, equilibrium, conservation, minimum-gap, and detector recount checks.
- [`../../../outputs/results/timestep_sensitivity.csv`](../../../outputs/results/timestep_sensitivity.csv): `dt = 0.05/0.10/0.20 s` comparison.
- [`../../../outputs/results/detector_audit.csv`](../../../outputs/results/detector_audit.csv): independent crossing-event recount.
- [`../../../outputs/plots/03_time_space_trajectories.png`](../../../outputs/plots/03_time_space_trajectories.png): vehicle trajectories.
- [`../../../outputs/plots/01_nominal_performance.png`](../../../outputs/plots/01_nominal_performance.png), [`02_disturbance_speed_traces.png`](../../../outputs/plots/02_disturbance_speed_traces.png), and [`04_stress_tests.png`](../../../outputs/plots/04_stress_tests.png): aggregate and changed-condition evidence.
- [`../../source_to_design_table.md`](../../source_to_design_table.md): preliminary Pathway A literature and model trace.

## Demonstration sequence

1. Use the time-space plot to identify free motion, slowing near the bottleneck, and the braking wave.
2. Show the conservation identity: generated vehicles must be accounted for as exited, still active, queued/unmet, or overflow.
3. Open `detector_audit.csv` and show that the reported count equals an independent crossing-event recount.
4. Compare the 0.05, 0.10, and 0.20-s runs. Explain that stable conclusions reduce the chance that the result is a numerical artifact.
5. State the preliminary Pathway A question and why ACC is required as the noncooperative comparison for CACC.

## Concepts to learn before the review

- Flow, speed, density, occupancy, throughput, queue, bottleneck, and conservation.
- How to read a time-space trajectory plot: slope is speed; flatter lines mean slower vehicles.
- Difference between boundary demand, actual entries, exits, residual queue, and dropped/unmet demand.
- Why detector counting needs an independent event log.
- Time-step sensitivity and boundary-condition testing.

Read Primer sections 2-7, 12, and 13 in [`../../traffic_engineering_primer.md`](../../traffic_engineering_primer.md).

## You are ready when you can answer

- How can you distinguish a real queue from a coding artifact?
- Why is `q = k v` dimensionally correct only when units are compatible?
- What does a line's slope mean in the trajectory plot?
- What evidence verifies detector count accuracy?
- Why is parameter tuning alone not validation?

## Final check

- [ ] Every plot has axes, units, and scenario labels.
- [ ] Residual queues and overflow are reported instead of silently discarded.
- [ ] The behavioral claim is narrower than the evidence and preserves negative results.
- [ ] Pathway A scope names a real vehicle-level mechanism, not just “CAVs are better.”

