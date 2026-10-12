# CEE 281 Design Project - Pathway A: Connected and Automated Vehicle Control

This repository is a complete, reproducible individual-project package for the Fall 2026 design guide. It implements a common freeway simulation and observation/TMC foundation, then compares human driving, noncooperative ACC, and cooperative ACC (CACC) in mixed traffic.

**New to traffic engineering?** Start with [`START_HERE.md`](START_HERE.md), then read the project-specific primer in [`deliverables/traffic_engineering_primer.md`](deliverables/traffic_engineering_primer.md). The exact files required at Intermediate 1, 2, 3, and Final are organized under [`deliverables/by_submission/`](deliverables/by_submission/README.md).

## Intermediate 1 (current submission)

```bash
bash run_int1.sh
```

Runs the unit tests, then the minimum case in `run_int1.py`: human drivers only, ramp meter off, one
braking disturbance, and the on-ramp merge at 1,600 m as the only bottleneck (random arrivals, seed 281,
plus a control run without ramp traffic). Expected result: speed-drop ratio 0.66; a mainline queue starting
at the merge, about 1 km long with stop-and-go waves; ramp queue at most 7; 0 unfinished vehicles; 0 overlaps.
Outputs go to `outputs/int1/`. Records: `deliverables/by_submission/01_intermediate_1/` (design record,
experiment record with pre-run predictions, contribution record). Live view: `python run_live.py`, then open
<http://127.0.0.1:8765>; the "Intermediate 1" scenario opens by default.

Note: for Intermediate 1 the human-driver parameters, the bottleneck (now the merge itself), the arrivals
and the merge rule were changed (see the design record). The final-pathway results described further below were produced with the earlier
baseline and will be regenerated.

## One-command reproduction

From this directory:

```bash
bash run_all.sh
```

The command creates/uses `.venv`, installs pinned dependencies, runs the verification suite, executes all scenarios, and rebuilds the final report and presentation PDFs.

For an already configured environment, the shorter experiment command is:

```bash
.venv/bin/python run_project.py
```

## Real-time interactive visualization

Launch the browser dashboard from this directory:

```bash
./start_visualization.sh
```

Alternatively, start it without automatically opening a browser:

```bash
.venv/bin/python run_live.py
```

Then visit <http://127.0.0.1:8765>. The dashboard runs the same `FreewaySimulation.step()` model used by the batch experiments—not a separate animation approximation. It includes all 12 Human/ACC/CACC scenarios, live road and on-ramp motion, bottleneck and detector overlays, CACC communication links/fallback state, ramp-meter and queue status, vehicle inspection, streaming metrics/charts, pause/reset/single-step, 0.25×–20× speed, and deterministic timeline seeking. Drag the roadway horizontally or use the **PAN** buttons to inspect the full corridor, including D2; **MERGE** returns to the on-ramp view. Panning changes only the camera position. Active vehicle bodies remain at a fixed 10×8-pixel size; braking is shown with lights/outlines, not by resizing the car. The detail-camera scale is chosen so the 2.0-m physical clearance remains visually separated. The **Record canvas** button records the road canvas and downloads a WebM video; the required MP4 remains at `outputs/detector_audit_clip.mp4`.

Keyboard shortcuts: `Space` plays or pauses, `R` resets, `→` advances one 0.1-s model step, `Shift` + `←/→` pans the camera, and `M` returns to the merge view. Stop the local server with `Ctrl+C`.

Typical runtime on a laptop is about 2 minutes. The simulator uses a declared seed (`281`) for equipment assignment and communication dropout. Arrival times are deterministic; repeated identical runs are therefore unnecessary except for the explicit numerical-sensitivity tests.

## Design question and answer

**Question.** At 50% and 100% equipment penetration, does delayed predecessor-acceleration feedforward (CACC) reduce a braking disturbance relative to otherwise identical ACC while maintaining throughput and bounded gaps in a mixed, open freeway simulation?

**Result.** At 50% penetration, CACC reduced the disturbance-amplification ratio by 12.5% and increased the minimum simulated gap by 11.4% relative to ACC, with unchanged throughput, but increased total delay by 14.6%. Relative to the already stable human baseline, CACC reduced delay by 65.2% but did not improve the disturbance ratio or braking count. The correct decision is therefore **revise before adoption**, not a general safety claim.

## What is implemented

- Open 2.5-km single-lane freeway with arrivals, exits, a 300-m speed bottleneck, an on-ramp queue, finite ramp storage, unmet-demand accounting, and a controlled ramp release.
- Human drivers using the Intelligent Driver Model (IDM).
- ACC using a bounded constant-time-headway proportional-derivative spacing controller.
- CACC using the same controller plus delayed predecessor-acceleration feedforward when the immediate predecessor is equipped.
- Explicit 0.1-s control updates, first-order command-to-motion response, `[-4, 2] m/s2` command bounds, local emergency braking, stale-message rejection, and ACC fallback.
- A controller-level braking-distance/next-step safety supervisor enforcing a 2.0-m physical net gap, plus a separately counted final numerical invariant.
- Virtual detectors that report 30-s count, mean speed, occupancy proxy, and quality flag.
- Exponential-smoothed state estimate and 30-s-ahead count forecast, compared on one held-out period with a 3-interval moving-average baseline.
- A missing-interval observation test, detector recount audit, and a short detector-audit video.
- A dependency-free local browser dashboard for real-time scenario playback and vehicle-level inspection.
- Fixed, unmetered, and ALINEA-like ramp-release comparisons.
- Nominal 0/50/100% penetration, communication degradation, high demand, stronger braking, ACC-vs-CACC ablation, and 0.05/0.1/0.2-s time-step sensitivity.

## Inputs

All scenario values are in [`configs/scenarios.json`](configs/scenarios.json). Internal units are seconds, metres, metres/second, and metres/second squared. Important inputs include demand, equipment penetration, controller type, message delay/dropout, braking pulse, time step, acceleration limits, and ramp-meter bounds.

Interface definitions and missing-value rules are in [`deliverables/interfaces.md`](deliverables/interfaces.md).

## Outputs

- `outputs/results/scenario_metrics.csv`: final evaluation record with demand, seed, model/controller versions, boundary queues, and required metrics.
- `outputs/results/experiment_record.csv`: prediction, change, result location, and interpretation for each experiment.
- `outputs/data/<scenario>/`: vehicle states, observations, estimates where applicable, control commands, decision traces, queue history, and exact detector crossing events.
- `outputs/plots/`: publication-ready labeled figures.
- `outputs/detector_audit_clip.mp4`: short video exercise for checking D1 crossings.
- `deliverables/final_report.pdf`: final technical report.
- `deliverables/final_presentation.pdf`: eight-minute presentation; source text and reproducible builder are included.
- `deliverables/design_record.md`: evolving Intermediate 1/2/3 and final design record.
- `deliverables/source_to_design_table.md`, `individual_contribution_record.md`, and `ai_use_and_verification.md`: required documentation.

## Verification

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The suite checks IDM free motion and equilibrium, vehicle conservation including boundary queues/overflow, nonnegative gaps, and independent detector-event recounts. The experiment suite additionally writes time-step sensitivity, detector-audit, forecast, stress-test, and residual-demand records.

## Known limitations

- The freeway is one lane; merging is represented by gap-accepted insertion, not lane changing.
- Parameters are literature-informed but not calibrated to a field trajectory dataset. This is verification and controlled simulation evidence, not external validation.
- The occupancy input is a virtual 50-m area occupancy proxy, so the ALINEA result is a foundation demonstration rather than a field-ready meter calibration.
- The 2.0-m numerical invariant is a final verification backstop; it was not activated in any of the 12 final scenarios, but neither it nor the controller supervisor is a production safety certification.
- No result establishes crash reduction. Minimum gaps and hard-braking counts are simulation indicators only.
- The official student UID should be checked on the title page and contribution record before submission; the contributor name is `Ruopeng`.

## Directory map

```text
configs/       scenario definitions
src/cavsim/    simulation, controllers, observation, plotting
tests/         verification checks
outputs/       generated data, metrics, plots, and video
deliverables/  report, presentation, design record, disclosures
scripts/       report and presentation builders
live_visualization/  local HTTP engine and interactive browser UI
```
