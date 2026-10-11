# Intermediate 1 - proposal and minimum simulation

**Guide timing:** after October 14.  
**Purpose:** show a bounded question, defensible model choice, explicit interfaces, individual ownership, and one runnable minimum example. At this point the guide asks you to consider both final pathways; the design record explains why Pathway A was selected over speed advice/signal control.

## Submit or show

- [`../../design_record.md`](../../design_record.md), section **Intermediate 1**: operational question, prediction, scope, considered alternative, and minimum case.
- [`../../references.md`](../../references.md) and [`../../source_to_design_table.md`](../../source_to_design_table.md): IDM original source and initial ACC/CACC sources.
- [`../../individual_contribution_record.md`](../../individual_contribution_record.md): individual role/ownership.
- [`../../interfaces.md`](../../interfaces.md): vehicle state, observation, estimate/forecast, control command, and evaluation-record fields.
- [`../../../configs/scenarios.json`](../../../configs/scenarios.json): units and initial parameter choices.
- [`../../../src/cavsim/core.py`](../../../src/cavsim/core.py): minimum car-following implementation.
- [`../../../tests/test_project.py`](../../../tests/test_project.py): runnable free-motion/equilibrium and small simulation checks.
- [`../../../README.md`](../../../README.md): one-command reproduction.

## Demonstration sequence

```bash
cd "/Users/rocair/Desktop/CEE281 Traffic Operation and Control/project"
.venv/bin/python -m unittest discover -s tests -v
```

Then point to `idm_acceleration()` in `src/cavsim/core.py` and explain these two minimum checks:

1. With no leader and zero speed, IDM should request its maximum acceleration parameter.
2. At the analytical equilibrium gap, IDM acceleration should be approximately zero.

## Concepts to learn before the review

- Position, speed, acceleration, vehicle length, net gap, spacing, and time headway.
- What a car-following model does and why IDM is a model rather than a controller.
- Why simulation uses a time step (`dt = 0.1 s`).
- Difference between verification (“did we implement the equation correctly?”) and validation (“does it reproduce real traffic?”).
- Why interfaces need units, timestamps, IDs, bounds, and missing-value rules.

Read Primer sections 1-5 and 13 in [`../../traffic_engineering_primer.md`](../../traffic_engineering_primer.md).

## You are ready when you can answer

- What is the exact operational question and what did you predict before running it?
- What does `s = x_leader - x_follower - vehicle_length` mean?
- Which IDM source supports the equation, and where is the equation implemented?
- What test would fail if the gap sign or vehicle ordering were wrong?
- Why did you choose Pathway A and what alternative did you reject?

## Final check

- [ ] Replace the provisional name/UID.
- [ ] Keep the proposal focused; do not claim that a simulation proves crash reduction.
- [ ] Make sure all units are seconds, metres, m/s, m/s2, vehicles, or veh/h as documented.
- [ ] Run the tests on the machine used for the demonstration.

