# Intermediate 1 - experiment record

Format: prediction -> change made -> result -> interpretation.

**Current Int 1 model: Run 8 (end of Section 9).** Earlier runs are kept as the record of what we tried:

| Run | Change | Outcome |
|---|---|---|
| 1 | bottleneck zone with T = 1.6 s (Sections 1-6) | predictions held; replaced after instructor feedback that the bottleneck should be the ramp merge itself |
| 2-3 | zone removed, merge moved to 1,600 m, higher demand (Section 7) | the merge caps the flow, but the excess waits on the ramp, not on the mainline |
| 4 | merge speed cap, merge braking limit that grows at low speed, random arrivals (Section 8) | a mainline queue forms, but braking reaches 13.7 m/s² and the ramp queue 30 vehicles |
| 5-7 | zipper merge and a 9 m/s² braking cap (Section 9) | a gridlock bug, then two rule errors, each found and fixed |
| 8 | a vehicle yields if it can stop with the merge braking limit (Section 9) | mainline queue of about 1 km with stop-and-go waves; ramp queue at most 7; all clear by 12.9 min |

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

## 7. Run 2 - the ramp merge is the bottleneck (after instructor feedback)

**Change made.** The artificial bottleneck zone (T = 1.6 s at 1,600-1,900 m) was removed: every driver keeps
T = 1.0 s everywhere. The on-ramp merge moved from 1,200 m to 1,600 m, where the zone used to start. Demand
was set so that the mainline alone fits but mainline plus ramp does not: mainline 1,900 veh/h (75% of the
lane capacity of 2,519 veh/h) plus ramp 700 veh/h = 2,600 veh/h (103%). A ramp vehicle merges if its new
follower need not brake harder than 4 m/s² (MOBIL safe deceleration; the earlier limit b = 1.5 m/s² would
lock ramp vehicles out of dense traffic, so merging could not slow the mainline). A control run without ramp
traffic was added. The platoon braking test is unchanged. Detectors stay at 1,450 m (D1, 150 m before the
merge) and 2,050 m (D2, 450 m after it).

**Pre-run predictions** (written 2026-10-12 20:58 UTC, before the run; the code was only checked with the
unit tests):
1. The platoon braking disturbance fades exactly as in Run 1 (ratio 0.66): the platoon is still upstream of
   the merge while it is measured, and nothing ahead of it changed.
2. Without ramp traffic, no queue forms (1,900 veh/h is 75% of capacity).
3. With ramp traffic, a queue forms just upstream of the merge (1,600 m) and spreads back past D1. The merge
   can pass at most about 2,340-2,520 veh/h (IDM queue discharge to capacity), so 81-264 veh/h are left over:
   about **13-44 vehicles** stored by 10 min, a queue of about **180-590 m** (tail at about 1.0-1.4 km).
   Some of the waiting is on the ramp, because ramp vehicles need gaps in dense traffic.
4. Merging forces followers to brake: hardest braking about 4-5 m/s²; no collisions.
5. Everything clears before 15 min; conservation holds; dt = 0.05 / 0.2 s change results by < 5%.

**Run 2 result.** Predictions 1, 2 and 4 held (ratio 0.66; no queue without ramp traffic; hardest braking
3.7 m/s², no collisions), but **prediction 3 failed**: no mainline queue formed. Mainline speeds at the merge
stayed near 100 km/h, while the ramp queue filled its 35-vehicle storage and 13 ramp vehicles could not enter.

**Diagnosis.** The "unmetered" mode still released ramp vehicles at the meter's upper bound of 900 veh/h (one
every 4 s), and a vehicle that found no safe gap waited 1 s before trying again. That let only about 500 ramp
vehicles per hour in, so the mainline never received enough merging traffic to slow down. With the meter
switched off, there should be no release limit.

**Run 3 change and prediction** (written 2026-10-12, before the rerun). Change: with the meter off,
the front ramp vehicle may try to merge at every 0.1-s step. Prediction: the same as Run 2 prediction 3 - a
mainline queue forms just upstream of the merge, spreads back past D1, and stores about 13-44 vehicles by
10 min; the ramp queue stays well below its storage; predictions 1, 2, 4 and 5 are unchanged.

**Run 3 results.** Prediction 3 failed again, in a different way: the merge now works, but the mainline
still does not queue. After the merge the road carries 2,528 veh/h at 74 km/h (D2, minutes 2-10), which is
the lane capacity (2,519 veh/h at 72 km/h). The mainline before the merge keeps about 100 km/h (D1 105 km/h).
The roughly 80 veh/h that do not fit wait on the ramp instead: 5, 9 and 12 vehicles at 5, 8 and 10 min,
cleared by 11 min, with no overflow. Predictions 1, 2, 4 and 5 held (ratio 0.66; no queue without ramp
traffic; hardest braking 4.0 m/s²; no collisions; all vehicles leave).

**Interpretation.** The merge is the bottleneck: it caps the flow at the lane capacity. But because a ramp
vehicle only enters a gap that is safe for the mainline follower, the mainline effectively has priority and
the excess queues on the ramp. Real unmetered merges usually break down the mainline, because merging drivers
enter slower and force their way into shorter gaps. Next decision: keep this polite merge (the congestion is
the ramp queue) or model forced merging (slower entry, harder braking imposed on followers) so that the
mainline jams upstream of the merge.

## 8. Run 4 - forced merging and random arrivals

**Change made.** Two merge settings from our earlier prototype, plus random arrivals:
- A ramp vehicle enters at most at 24.6 m/s (89 km/h; AASHTO Green Book Exhibit 10-70, speed reached at the
  merge on a 75-mph highway), because a short acceleration lane does not let it reach the mainline speed.
- The braking a merge may impose rises as the follower gets slower: 4 m/s² at the desired speed, up to
  17 m/s² at standstill (speed-dependent safe deceleration of the MOBIL code on traffic-simulation.de).
- Arrivals are random (Poisson) with the same mean rates, seed 281 (one seed). Over the 10 min: 313 mainline
  and 117 ramp vehicles; mainline gaps 1.9 s on average, from 0.02 s to 14 s.

**Pre-run predictions** (written 2026-10-12 21:09 UTC, before the run):
1. Platoon braking ratio unchanged at 0.66 (the platoon is ahead of every new arrival while it is measured).
2. Without ramp traffic, still no queue (75% of capacity), although random bunches cause short slowdowns.
3. With ramp traffic, the mainline now jams: ramp vehicles entering about 15 km/h slower than the mainline
   make followers brake, and once the mainline slows, the larger allowed braking lets ramp vehicles keep
   squeezing in. A queue forms just upstream of the merge and spreads back, roughly 0.2-1.5 km long
   (13-110 vehicles, depending on how far merging lowers the flow through the merge: 0-22%).
4. No collisions, but the hardest braking may exceed 9 m/s², which no real car can do (a risk of the 17 m/s²
   limit without a physical braking cap).
5. The queue clears within about 4 min after arrivals stop, so by about 15 min.

**Run 4 results** (`python run_int1.py`, seed 281):
| Prediction | Result | |
|---|---|---|
| 1. ratio unchanged | 0.66 | supported |
| 2. no queue without ramp traffic | no queue | supported |
| 3. mainline jams upstream of the merge, 0.2-1.5 km, 13-110 vehicles | queue starts at the merge (1,600 m) at 5.2 min, spreads back to 1.29 km (about 310 m), 23 vehicles; mainline in the last 300 m before the merge averages 43 km/h (5-10 min); D1 below 40 km/h at 9 min; ramp queue up to 30, no overflow | supported |
| 4. no collisions; braking may exceed 9 m/s² | 0 collisions, smallest gap 2.1 m; **hardest braking 13.7 m/s²** | supported, and a problem: no real car brakes that hard |
| 5. clears by about 15 min | last slow vehicle at 12.6 min, 0 vehicles left | supported |
| time step 0.05 / 0.1 / 0.2 s | ratio 0.655 / 0.658 / 0.664; delay 5.63 / 5.60 / 5.53 veh·h; D1 onset 510 / 540 / 540 s | < 2% except the D1 onset (one 30-s interval) |

**Interpretation.** With ramp vehicles entering slower than the mainline and allowed to force harder braking
when traffic is slow, the merge itself creates a mainline queue that spreads back past D1, and no queue forms
without ramp traffic, so the merge is the cause. Open issue: the 17 m/s² merge limit lets a follower brake
13.7 m/s². A physical braking cap of about 9 m/s² on vehicle motion (as in our earlier prototype) is the next fix.

## 9. Runs 5-8 - zipper merging in slow traffic and a physical braking limit

**Why.** In Run 4 the ramp queue grew by about 6 vehicles per minute once the mainline jammed (0 at 4 min,
30 at 10 min), i.e. almost no ramp vehicle could merge into the jam: queued mainline cars stand about 7.5 m
apart, a ramp car needs at least 9 m (2 m + 5 m + 2 m), and mainline drivers never left space. Real drivers
take turns (zipper merge). Run 4 also had braking of 13.7 m/s², which no real car can do.

**Change made.**
- Zipper merge: when a ramp vehicle is waiting and the first mainline vehicle within 100 m before the merge
  drives slower than 40 km/h, that vehicle leaves one slot by following an imaginary car at the merge point.
  After a ramp vehicle enters, the next slot goes to the mainline, and so on. 40 km/h is a design choice (the
  same threshold we use for "congested").
- Human drivers cannot brake harder than 9 m/s² ("maximum deceleration of about 9 m/s²", traffic-simulation.de
  MOBIL page). Collisions are still counted, not prevented.

**Pre-run predictions** (written 2026-10-12 21:15 UTC, before the run):
1. Platoon braking ratio unchanged (0.66); no queue without ramp traffic.
2. The ramp queue stays small (at most about 10 vehicles instead of 30): during the jam, ramp vehicles get
   every other slot, which is more than the ramp demand needs.
3. The waiting moves to the mainline: about as many vehicles wait in total as in Run 4 (about 50 at 10 min),
   but now mostly on the mainline, so the mainline queue roughly doubles (about 40-55 vehicles, 0.5-0.75 km,
   tail near 0.9-1.1 km) and D1 drops below 40 km/h earlier than in Run 4.
4. Hardest braking at most 9 m/s²; no collisions.
5. Everything clears by 15 min.

**Run 5 result: gridlock (predictions 2, 3 and 5 failed).** The mainline before the merge came to a standstill
(3 km/h on average), the queue reached 0.41 km with 172 vehicles, the ramp overflowed (22 vehicles turned away),
and 229 vehicles were still in the system at 15 min.

**Diagnosis (a bug in the zipper rule).** At 420 s the first mainline vehicle before the merge stood with its
front 1.1 m inside the slot it was told to leave. It had been selected to yield when it was already too close,
braked at 9 m/s² and stopped there. The ramp vehicle then never found the 2-m gap it needs, and the mainline
vehicle kept waiting for the ramp vehicle: a deadlock.

**Run 6 change and prediction** (written 2026-10-12, before the rerun). Change: only a mainline vehicle that can
still stop at least s0 = 2 m behind the slot yields; a vehicle already closer passes and the next one yields.
Prediction: the same as Run 5 predictions 1-5.

**Run 6 result: no gridlock, but the ramp still overflows (prediction 2 failed).** Mainline queue 32 vehicles,
back to 1.19 km (longer than Run 4's 23 vehicles and 1.29 km), cleared at 13.3 min; but the ramp queue reached
its storage of 35 and 15 vehicles were turned away. From minute 7 to 9 no ramp vehicle merged.

**Diagnosis.** The yielding vehicle followed an imaginary car that had the real leader's speed, so it closed in
on the slot without braking. Once it came within 2 m of the slot it no longer qualified to yield and drove on,
while the vehicle that had just passed was still too close to the merge point for the ramp vehicle to fit ahead.

**Run 7 change and prediction** (written 2026-10-12, before the rerun). Change: the imaginary car stands still,
so the IDM brakes in time; only a vehicle that can stop behind the slot with its comfortable deceleration b
yields, otherwise it passes and the next one yields. Prediction: the same as Run 5 predictions 1-5.

**Run 7 result: the zipper never acts (prediction 2 failed).** Ramp queue up to 31 (no overflow), mainline queue
22 vehicles back to 1.31 km, cleared at 12.6 min: almost the same as Run 4. While a ramp vehicle waited, the
first mainline vehicle could not stop comfortably behind the slot 85% of the time, so it drove on. In a dense
queue at about 20 km/h every vehicle is that close, so no one ever yielded.

**Run 8 change and prediction** (written 2026-10-12, before the rerun). Change: a mainline vehicle yields if it
can stop behind the slot with the braking a merge may impose on it (the speed-dependent limit, at most 9 m/s²),
instead of the comfortable 1.5 m/s². At 20 km/h this means it needs about 2 m to stop. Prediction: the same as
Run 5 predictions 1-5.

**Run 8 results (current model).**
| Run 5 prediction | Result | |
|---|---|---|
| 1. ratio 0.66; no queue without ramp traffic | 0.66; no queue | supported |
| 2. ramp queue at most about 10 | at most 7, no overflow | supported |
| 3. waiting moves to the mainline; about 40-55 vehicles, 0.5-0.75 km | 103 vehicles, queue back to 0.61 km (about 1 km long); D1 below 40 km/h at 7 min (Run 4: 9 min) | direction supported, size larger than predicted |
| 4. braking at most 9 m/s², no collisions | 9.0 m/s² (the limit), 0 collisions, smallest gap 1.8 m | supported |
| 5. clears by 15 min | last slow vehicle at 12.9 min, 0 left | supported |
| time step 0.05 / 0.1 / 0.2 s | ratio 0.655 / 0.658 / 0.664; delay 8.36 / 8.56 / 8.88 veh·h; D1 onset 420 s in all | < 4% |

During the jam (6-10 min) the mainline passes 870 veh/h before the merge and 1,500 veh/h after it, so ramp
vehicles take about 630 veh/h, roughly every other slot. The queue is larger than predicted because every
yielding vehicle stops completely: the merge then passes only 1,500 veh/h, 40% below the lane capacity. A real
merge probably loses less, because drivers adjust their speed earlier instead of stopping, so this rule probably
overstates the capacity drop (not checked against data).

**Stop-and-go waves.** Run 1 expected stop-and-go waves inside the queue but saw none. In Run 8 they appear: the
129 vehicles that slowed below 5 km/h in the 700 m before the merge came to a stop (below 3 km/h) 3.6 times each
on average, up to 8 times (from `trajectories.csv`). Each zipper yield makes a mainline vehicle stop at the merge,
and the queue moves at about 12 km/h, inside the speed range where the linear stability check says IDM
disturbances grow (about 4-72 km/h for T = 1.0 s), so these stops travel back through the queue instead of fading.

## 10. Proposal experiment: time gap x ramp demand (predictions written before running)

Written **2026-10-18 19:46 UTC**, before any of cases P1-P3, P5, P6 was run. P4 is the current model (Run 8).
The same table is in the written proposal (Section 2, "Run 1-6").

**Question.** Under what desired time gap and on-ramp demand does an on-ramp merge turn into a persistent mainline
queue with stop-and-go waves?

**Change.** The desired time gap T of every driver is 0.8, 1.0 or 1.2 s, and the ramp demand is 200 or 700 veh/h.
Everything else is as in Run 8 (mainline 1,900 veh/h, Poisson arrivals with seed 281, zipper merge, 9 m/s² cap).

**Reasoning.** Lane capacity C from the IDM equilibrium relation: 2,967 / 2,519 / 2,191 veh/h for T = 0.8 / 1.0 /
1.2 s. A queue persists only when 1,900 + ramp demand > C, and then grows by at least (demand - C) vehicles per
hour. The linear stability condition of the IDM gives string instability below 75 / 72 / 70 km/h for these T, so
any queue (well below 70 km/h) should carry stop-and-go waves moving backward at about 15 km/h.

| Case | T [s] | C [veh/h] | Ramp [veh/h] | Demand / C | Prediction |
|---|---|---|---|---|---|
| P1 | 0.8 | 2,970 | 200 | 71% | no persistent queue |
| P2 | 0.8 | 2,970 | 700 | 88% | no persistent queue |
| P3 | 1.0 | 2,520 | 200 | 83% | no persistent queue |
| P4 | 1.0 | 2,520 | 700 | 103% | queue of at least 14 veh after 10 min; stop-and-go waves (already seen in Run 8) |
| P5 | 1.2 | 2,190 | 200 | 96% | no persistent queue (closest to capacity) |
| P6 | 1.2 | 2,190 | 700 | 119% | larger queue, at least 68 veh after 10 min; stop-and-go waves |

A queue is **persistent** if mainline vehicles before the merge stay below 40 km/h for more than 2 min.
**Supported** if queues form only in P4 and P6, P6's queue is larger, and both carry waves. **Challenged** if a
queue forms in P5 or P2 (demand below capacity): the merging itself would then break the flow before capacity is
reached. A queue without waves would challenge the stability argument.
