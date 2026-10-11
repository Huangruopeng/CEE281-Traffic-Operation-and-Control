# Intermediate 3 - observation, prediction, TMC, and CAV prototype

**Guide timing:** after November 16.  
**Purpose:** show the full observe-estimate-predict-decide-act-evaluate loop, exchange data through declared interfaces, compare ramp-control baselines, and demonstrate an initial vehicle-controller prototype.

## Submit or show

- [`../../design_record.md`](../../design_record.md), through **Intermediate 3**.
- [`../../../src/cavsim/observation.py`](../../../src/cavsim/observation.py): detector audit, exponential smoothing, moving-average baseline, held-out forecast evaluation, and missing-input condition.
- [`../../../outputs/results/forecast_records.csv`](../../../outputs/results/forecast_records.csv) and [`forecast_metrics.csv`](../../../outputs/results/forecast_metrics.csv): identical 30-s horizons and held-out evaluation.
- [`../../../outputs/results/observations_missing_test.csv`](../../../outputs/results/observations_missing_test.csv): explicit missing values and quality flags.
- [`../../../outputs/plots/05_forecast_evaluation.png`](../../../outputs/plots/05_forecast_evaluation.png): forecast comparison.
- [`../../../outputs/results/tmc_comparison.csv`](../../../outputs/results/tmc_comparison.csv), [`../../../outputs/plots/06_sensitivity_tmc.png`](../../../outputs/plots/06_sensitivity_tmc.png), and a representative `control_commands.csv`: unmetered, fixed, and ALINEA-like ramp release.
- A representative [`../../../outputs/data/nominal_cacc_50/decision_trace.csv`](../../../outputs/data/nominal_cacc_50/decision_trace.csv): measured inputs, delayed message, bounded command, and fallback state.
- [`../../interfaces.md`](../../interfaces.md): component-exchange evidence.
- [`../../../outputs/detector_audit_clip.mp4`](../../../outputs/detector_audit_clip.mp4): short video counting exercise.

## Demonstration sequence

1. Trace one detector interval from crossing events to observation count.
2. Explain the 30-s forecast target and why both methods are evaluated on the same held-out periods.
3. Show one deliberately missing interval and the `missing_input_hold` behavior.
4. Trace one TMC decision: observation -> occupancy error -> bounded ramp rate -> traffic response.
5. Trace one CACC row: local speed/gap/relative speed -> delayed predecessor acceleration -> command; then show an `ACC_fallback` row.

## Concepts to learn before the review

- Measurement versus hidden simulator truth.
- Estimation versus prediction and why development/evaluation periods must be separated.
- Moving average, exponential smoothing, forecast horizon, and MAE.
- Feedback control, actuator bounds, storage protection, and fallback.
- Component exchange: one module should consume the declared CSV fields without knowing another module's internals.
- ACC versus CACC and what delayed/missing communication changes.

Read Primer sections 6-11 and 13 in [`../../traffic_engineering_primer.md`](../../traffic_engineering_primer.md).

## You are ready when you can answer

- What can the detector actually measure, and what remains unavailable?
- Which data selected the smoothing parameter and which data scored it?
- Why does lower MAE under one missingness pattern not prove missing data help?
- What did the ramp controller know at a particular decision time?
- Which CACC input disappears during communication dropout, and what is the fallback?

## Final check

- [ ] Forecast methods use the same horizon and evaluation intervals.
- [ ] Missing quantities remain blank/NaN and carry a quality flag.
- [ ] Ramp commands include bounds, units, reason, and fallback state.
- [ ] The initial CAV prototype changes vehicle commands, not only labels or display parameters.

