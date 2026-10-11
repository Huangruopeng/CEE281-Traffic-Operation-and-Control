# Final - executable Pathway A system, report, and presentation

**Guide timing:** after December 2.  
**Purpose:** deliver an executable CAV control mechanism, fair baseline comparisons, stress/degraded tests, limitations, source traceability, individual contribution, and an eight-minute individual presentation.

## Primary files to submit

- [`../../final_report.pdf`](../../final_report.pdf): six main pages plus references/traceability.
- [`../../final_presentation.pdf`](../../final_presentation.pdf): final presentation.
- [`../../presentation_script.md`](../../presentation_script.md): eight-minute timing and defense notes.
- [`../../../README.md`](../../../README.md), [`../../../run_all.sh`](../../../run_all.sh), and [`../../../requirements.txt`](../../../requirements.txt): reproducible package.
- [`../../../src`](../../../src), [`../../../configs/scenarios.json`](../../../configs/scenarios.json), and [`../../../tests`](../../../tests): code, configuration, and checks.
- [`../../../outputs/results/scenario_metrics.csv`](../../../outputs/results/scenario_metrics.csv), [`../../../outputs/results/experiment_record.csv`](../../../outputs/results/experiment_record.csv), [`../../../outputs/plots`](../../../outputs/plots), and representative detailed data.
- [`../../source_to_design_table.md`](../../source_to_design_table.md), [`../../individual_contribution_record.md`](../../individual_contribution_record.md), and [`../../ai_use_and_verification.md`](../../ai_use_and_verification.md).
- [`../../../CEE281_PathwayA_Submission.zip`](../../../CEE281_PathwayA_Submission.zip): packaged copy of the above.

Use [`../../submission_checklist.md`](../../submission_checklist.md) for the full guide-to-evidence audit.

## Required Pathway A comparisons

| Requirement | Project evidence |
|---|---|
| Credible human baseline | `nominal_human` |
| At least two nonzero penetration settings | ACC/CACC at 50% and 100% |
| Noncooperative comparison isolating communication | matched ACC versus CACC |
| Delay/dropout or noncompliance | `degraded_cacc_50`: 0.8-s delay, 30% dropout |
| Changed demand | `high_demand_*` |
| Stronger disturbance | `strong_brake_*` |
| Throughput, delay, trajectories, amplification, gaps/braking | `scenario_metrics.csv` and plots 01-04 |
| CEE281 comparison/ablation | CACC feedforward enabled versus matched ACC disabled |

## Four-minute demonstration plan

1. Start the dashboard with `./start_visualization.sh` and select `nominal_cacc_50`.
2. Point out the lead-vehicle disturbance, simultaneous following response, fixed-size vehicles, and ramp merge.
3. Select an equipped vehicle and identify speed, gap, acceleration, message state, and safety override state.
4. Switch to `degraded_cacc_50` and explain ACC fallback under delayed/dropped communication.
5. Return to the slides for the measured comparison and limitations.

## Four-minute explanation/defense plan

1. State the bounded question and prediction.
2. Explain human IDM, ACC, and the one extra CACC feedforward term.
3. Give the 50% ACC/CACC result: amplification `0.722 -> 0.631`, minimum gap `4.670 -> 5.203 m`, delay `1.700 -> 1.947 veh-h`, unchanged throughput.
4. Explain the degraded-message and high-demand results.
5. Defend **revise before adoption** because hard braking, supervisor dependence, single-lane merge abstraction, and lack of field calibration remain.

## Concepts you must own

- Every symbol and input in the IDM/ACC/CACC equations.
- Why ACC is the key ablation for evaluating communication.
- Penetration, delay, dropout, fallback, actuation lag, and bounded command.
- Throughput, total delay, disturbance amplification, minimum gap, hard-braking events, residual demand.
- Verification versus validation and why no simulation result here proves crash reduction.
- Why a supported negative result can be a correct engineering conclusion.

Read the entire [`../../traffic_engineering_primer.md`](../../traffic_engineering_primer.md), then rehearse [`../../presentation_script.md`](../../presentation_script.md).

## Final check

- [ ] Replace the provisional name/UID and follow the instructor's naming convention.
- [ ] Run `bash run_all.sh` and confirm all tests pass.
- [ ] Personally inspect the report, slides, CSV metrics, and detector video.
- [ ] Restart the live server after code changes; do not demonstrate from a stale process.
- [ ] Practice explaining one decision-trace row without memorized wording.
- [ ] Never say “CACC is safer”; say exactly which simulated indicators improved or worsened.

