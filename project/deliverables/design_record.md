# Evolving design record

## Intermediate 1 - proposal, sources, roles, interface, minimum case

### Operational question and prediction

The preliminary question was whether predecessor-acceleration communication can suppress a finite lead-braking disturbance beyond what local ACC can accomplish in mixed traffic. The initial prediction was that CACC would reduce the maximum follower speed loss relative to ACC, while command saturation and a local emergency rule would preserve nonnegative gaps. A second prediction was that the benefit would weaken under message delay/dropout.

Pathway A was selected because it supports a bounded vehicle-level comparison and reuses the common simulator, detector, forecast, and TMC interfaces. The project is scoped as an individual submission. `Ruopeng` owns model design, controller implementation, integration, tests, experiments, interpretation, and presentation; the official course UID must be confirmed before submission.

### Model and minimum example

Human driving uses the IDM from Treiber, Hennecke, and Helbing. The minimum case is a follower approaching a constant-speed leader. The checks predict maximum acceleration on an empty road and zero acceleration at the analytical equilibrium gap. Both automated controllers use a constant-time-headway desired gap, bounded acceleration, and first-order actuation. CACC adds only predecessor-acceleration feedforward; disabling that term produces the ACC ablation.

The minimum exchange formats are documented in `interfaces.md`. A small run is exercised by `tests/test_project.py`; it also verifies conservation and the detector recount.

### Considered alternative

A connected speed-advisory controller was considered, but it would require an explicit human compliance distribution and would make the ACC/CACC communication ablation less direct. The cooperative longitudinal-control pathway was therefore selected.

## Intermediate 2 - verified simulation, detectors, behavioral investigation

### Simulation design

The final common environment is a 2.5-km, one-lane, open freeway. It contains deterministic mainline/ramp arrivals, finite ramp storage, a gap-accepted on-ramp insertion at 1.2 km, a 300-m speed bottleneck beginning at 1.6 km, and downstream exit. A 12-vehicle initial platoon receives one four-second lead-braking disturbance. Demand ends at 600 s and the run continues to 900 s to clear nominal residual queues.

The numerical update is semi-ballistic with explicit speed nonnegativity. A controller-level supervisor checks one-step clearance and differential stopping distance, applies immediate bounded braking when needed, and preserves a configured 2.0-m physical net gap. A separately counted numerical invariant remains as a final backstop. Delay accumulates for moving vehicles and all boundary/ramp waiting vehicles. Ramp overflow and residual demand remain in the evaluation record rather than being discarded.

### Verification evidence

- Free motion: an empty-road vehicle at rest accelerates at the IDM `a` parameter.
- Equilibrium: the analytical IDM equilibrium gap produces acceleration numerically equal to zero.
- Conservation: generated vehicles equal exited plus in-system plus boundary/residual/overflow vehicles.
- Gaps: all 12 final scenarios remain above the configured 2.0-m net-gap floor; the final numerical collision guard records zero activations.
- Detector audit: exact crossing-event recount equals reported counts in all 10 labeled sample intervals.
- Time-step sensitivity: the human delay changes from 5.586 to 5.607 veh-h across 0.05-0.20 s; CACC-50 delay changes from 1.956 to 1.917 veh-h. The qualitative conclusion is stable and the final collision guard remains unused.

### Behavioral result

The human baseline disturbance amplification is below one, so the selected human parameters already dissipate the initial disturbance. This is an important negative condition: CACC cannot honestly be claimed to improve the human amplification metric in this setup. The design question was narrowed to the incremental value of CACC over matched ACC, with the human baseline retained for credibility.

## Intermediate 3 - observation/forecast, component exchange, common TMC, prototype

### Observation and forecasting

Two virtual detectors report 30-s count, mean crossing speed, and a 50-m occupancy proxy. An independently generated crossing-event log is used for recount. The forecast target is the next 30-s count. Exponential smoothing is tuned only on the first half of the intervals and evaluated on the same held-out second half as a 3-interval moving average.

The complete-data evaluation MAE is 1.820 vehicles/30 s for exponential smoothing versus 2.311 for the moving average. When every fifth interval is withheld, the smoothing MAE unexpectedly decreases to 1.618. This does not prove that missing data help; it indicates that the particular removed updates were noisy and that more missingness patterns/seeds are required before generalization.

### Common TMC

The ramp module compares unmetered, fixed, and occupancy-feedback release under identical demand. Total delay is 5.442, 5.531, and 5.590 veh-h, respectively. The ALINEA-like loop functions and remains bounded, but does not improve this lightly constrained, proxy-occupancy case. A field-oriented revision would require a calibrated occupancy target, a heavier bottleneck, and detector placement study.

### Initial CAV prototype

The prototype logs every measured input, message age/validity, bounded command, and fallback state. The command-to-motion response is first-order with a 0.5-s time constant. The cooperative input is exactly the delayed acceleration of the immediate equipped predecessor; a human predecessor, missing message, or message older than 1.0 s disables feedforward and uses ACC.

## Final - experiments, finding, and design decision

### Fair experiment matrix

All controller comparisons share arrival schedules, initial platoon, seed, bottleneck, ramp logic, run length, detector definitions, and disturbance timing. The matrix contains human 0%, ACC 50/100%, CACC 50/100%, CACC-50 with 0.8-s delay and 30% dropout, high-demand human/ACC/CACC, and stronger-braking human/ACC/CACC. The ACC-vs-CACC pair is the CEE281 ablation.

### Main finding

At 50% penetration, CACC reduces amplification from 0.722 to 0.631 (-12.5%) and increases the minimum gap from 4.670 to 5.203 m (+11.4%) relative to ACC, but total delay rises from 1.700 to 1.947 veh-h (+14.6%). Throughput stays at 1288 veh/h. Against the human baseline, CACC reduces total delay by 65.2%, but the human disturbance ratio is lower (0.596) and its hard-braking count is lower (62 versus 80). The safety supervisor intervenes 51 times in CACC-50 and the final numerical guard never activates.

Communication degradation increases CACC-50 delay by 3.8%, amplification by 5.5%, and hard-braking events by 18.8%; fallback keeps commands and gaps bounded. Under high demand, CACC-50 exits 377 vehicles compared with 347 for human driving and reduces delay by 26.7%, but hard-braking events rise from 33 to 76. Under the stronger brake, CACC delay is 2.2% higher than ACC while its minimum gap is 39.2% larger in that one run.

### Decision

The evidence supports the narrow claim that predecessor acceleration has incremental value over matched ACC for disturbance response and gap preservation. It does not support adopting the controller unchanged: automated hard-braking frequency, safety-supervisor dependence, the single-lane merge abstraction, and lack of field calibration remain material. The next design cycle should retune headway/gains under constraints on hard braking and supervisor use, test multiple stochastic arrivals/equipment placements, and validate on measured trajectories.

### Changes from review/self-review

No instructor feedback was supplied with this workspace. The recorded self-review changes were: (1) replacing a generic CAV parameter change with an explicit ACC/CACC command interface; (2) adding boundary-delay and overflow accounting; (3) adding ACC as a communication ablation; (4) adding message-age fallback and command bounds; (5) adding missing-observation and time-step tests; and (6) changing the conclusion from “CACC improves stability” to the narrower, evidence-supported statement above.

