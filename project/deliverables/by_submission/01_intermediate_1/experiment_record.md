# Intermediate 1 - experiment record

Format: prediction -> change made -> result -> interpretation.
Predictions (Section 3) were written on **2026-10-11 22:40 UTC, before the run**. Before that, the
modified code was only checked with the unit tests (at most 90 s of simulation with five vehicles).

## 1. Problem

**System.** One-lane freeway, 2.5 km. For the first 10 min, vehicles enter at a constant rate:
mainline at x = 0 m, 1,500 veh/h (one every 2.4 s); on-ramp at x = 1,200 m, 360 veh/h (one every
10 s). After 10 min no new vehicles arrive, and the run continues to 15 min so every vehicle can leave
at x = 2,500 m. Twelve vehicles start as a platoon at 79 km/h. The **bottleneck** is the 300 m zone at
1,600-1,900 m, where drivers keep a longer time gap. Detectors: D1 at 1,450 m, D2 at 2,050 m (30-s reports).
The ramp meter is off (ramp control is Intermediate 3).

**Question.** Does a braking disturbance fade, grow, or turn into a lasting queue near the bottleneck?

**Why this scope.** One lane, identical drivers, constant arrivals, one disturbance, one bottleneck,
no control: every result can be traced to the IDM equation and to one place in the code.

## 2. Model and sources

| Item | Value | Source |
|---|---|---|
| Car following | IDM: a_max[1 - (v/v0)^4 - (s*/s)^2], s* = s0 + vT + vΔv/(2√(ab)) | Treiber, Hennecke & Helbing (2000) |
| v0, T, s0, a, b, δ | 120 km/h, 1.0 s, 2 m, 1.0 m/s², 1.5 m/s², 4 | Treiber & Kesting (2013), Table 11.2 (cars, freeway) |
| Vehicle length | 5 m | Treiber, Hennecke & Helbing (2000), Table 1 |
| Bottleneck | T = 1.6 s inside 1,600-1,900 m | method and value: Treiber, Hennecke & Helbing (2000) (local increase of T; Table 1 value). Position and length: design choice |
| Entry and merge | admitted only if no vehicle must brake harder than b; ramp vehicle enters at its new leader's speed | design choice using only IDM and b |

Changes from the teammate's baseline: textbook IDM values; human drivers are pure IDM (the safety
supervisor and braking limits now apply only to automated vehicles); bottleneck as a local time-gap
increase instead of an unsourced 18 m/s speed zone; one IDM-based entry/merge rule instead of fixed gaps.

## 3. Pre-run predictions

From the IDM equilibrium relations: the lane can carry at most 2,519 veh/h outside the zone, but only
1,743 veh/h inside it.

**Prediction 1.** The braking disturbance (one platoon vehicle brakes at -2.5 m/s² for 4 s) fades as it
passes back: the largest speed drop among the 8 followers is smaller than the braking vehicle's own drop
(ratio about 0.6-0.95). Reason: the platoon drives at 79 km/h with gaps longer than IDM needs, and a
linear stability check of the IDM says disturbances fade at this speed.

**Prediction 2.** Because 1,860 veh/h arrive but the zone passes only 1,743 veh/h, a queue forms just
upstream of the zone (not at the ramp), grows back toward the ramp (about 18-39 vehicles stored), and
clears after arrivals stop at 10 min.

Other expectations written at the same time: D1 drops below 40 km/h at 190-320 s; D2 stays above 80 km/h;
traffic inside the queue moves in stop-and-go waves; the ramp queue stays below its storage of 35.

## 4. Checks

Vehicle conservation (generated = exited + still in system), no collisions (negative gaps counted, not
prevented), smallest gap, hardest braking, and the same run at time steps of 0.05 s and 0.2 s.

## 5. Results (`python run_int1.py`, outputs in `outputs/int1/`)

| | Expected | Result | |
|---|---|---|---|
| Prediction 1: speed-drop ratio | 0.6-0.95 | **0.66** (followers lose at most 66% of the leader's speed drop) | supported |
| Prediction 2: where the queue starts | upstream of 1,600 m | 1,621 m (zone entrance) at 3.1 min | supported |
| Prediction 2: vehicles stored, queue end | 18-39, near the ramp | 24 vehicles, queue end at 1.32 km | supported |
| Prediction 2: recovery | clears after 10 min | last slow vehicle at 13.2 min, none left at 15 min | supported |
| D1 below 40 km/h / D2 minimum | 190-320 s / > 80 km/h | 330 s / 86 km/h | D1 slightly late |
| Stop-and-go in the queue | yes | **no**: smooth queue, 27 km/h on average, never below 15 km/h | not supported |
| Ramp queue | < 35 | 32 | supported, but see limitation |
| Checks | | conservation holds; 0 collisions; smallest gap 5.7 m; hardest braking 3.4 m/s²; dt 0.05/0.2 s change the ratio by < 1% and delay by < 3% | passed |

Figures: `time_space_all_vehicles.png` (queue at the zone entrance), `disturbance_speed_traces.png`
(Prediction 1), `detectors_and_ramp_queue.png` (D1, D2, ramp queue).

## 6. Interpretation and limitations

- A single braking event in free-flowing traffic fades; a demand above the bottleneck's capacity creates a
  queue in front of it, which clears once arrivals stop. Both predictions hold.
- The expected stop-and-go waves did not appear. The queue is short (about 300 m) and nothing disturbs it
  after it forms. Next test: a braking event inside the queue.
- **Limitation: merge rule.** From minute 5 to 10 no ramp vehicle merges. A ramp vehicle enters at the
  speed of its new leader, which is already slowing for the queue ahead, while the follower is still fast,
  so every gap fails the "no braking harder than b" rule. This comes from our simplified one-point merge,
  not from the IDM. It will be revised in Intermediate 2 (first candidate: enter at the follower's speed).
- **Limitation: demand.** Arrivals stop abruptly at 10 min; real demand would taper off.
