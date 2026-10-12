# Start here - zero-background project map

This page is the recommended entry point if you have not studied traffic engineering before. The final report and code are already complete; your remaining task is to understand, explain, and submit the right evidence at each checkpoint.

## 1. Use the project in this order

1. Read [`deliverables/traffic_engineering_primer.md`](deliverables/traffic_engineering_primer.md). It explains the traffic concepts in beginner-friendly language and uses the same terms as the report and dashboard.
2. Open [`deliverables/by_submission/README.md`](deliverables/by_submission/README.md) and select the current submission stage.
3. Follow that stage's checklist. Each checklist tells you what to submit, what to demonstrate, and what you must be able to explain.
4. Run the project once with `bash run_all.sh` and the live dashboard with `./start_visualization.sh`.
5. Before presenting, practice the questions at the end of the primer without reading the answers.

## 2. Four formal technical submissions

| Stage | Guide timing | Main purpose | Stage guide |
|---|---|---|---|
| Intermediate 1 | after October 14 | Proposal, model/source choice, roles, interfaces, minimum simulation | [`01_intermediate_1`](deliverables/by_submission/01_intermediate_1/README.md) |
| Intermediate 2 | after October 28 | Verified simulation/detectors, behavioral investigation, preliminary Pathway A scope | [`02_intermediate_2`](deliverables/by_submission/02_intermediate_2/README.md) |
| Intermediate 3 | after November 16 | Observation/forecast, component exchange, working basic TMC, initial CAV prototype | [`03_intermediate_3`](deliverables/by_submission/03_intermediate_3/README.md) |
| Final | after December 2 | Executable CAV system, fair comparisons, stress tests, limitations, report and presentation | [`04_final`](deliverables/by_submission/04_final/README.md) |

The course guide describes one continuing project. Do not create four unrelated reports. Update the same design record and repository while adding evidence at each stage.

## 3. One-sentence project explanation

This project simulates a one-lane freeway and asks whether cooperative adaptive cruise control (CACC), which receives a delayed acceleration message from the preceding equipped vehicle, improves braking-disturbance behavior compared with matched noncooperative ACC while preserving throughput and bounded vehicle gaps.

## 4. The conclusion you should defend

CACC has incremental value over matched ACC in the selected 50% penetration test: disturbance amplification decreases by 12.5% and minimum gap increases by 11.4%, but delay increases by 14.6%. The evidence therefore supports **revise before adoption**, not a general safety or crash-reduction claim.

## 5. Immediate administrative check

The project uses the contributor name `Ruopeng`. Add the official course UID before submission, and check Canvas for any file-naming rule that is not stated in the supplied design guide.

