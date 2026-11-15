# Experiment record (mid-report onward)

Earlier records: `../01_intermediate_1/experiment_record.md` (Runs 1-8 of the model build, and the six-run
time gap x ramp demand predictions of Oct 18 with their results).

## 1. Model change before the mid-report runs (2026-11-14)

- Removed the braking platoon that started on the road at t = 0 (an Intermediate 1 check, unrelated to the
  question). The road now starts empty.
- Removed the old template's ACC/CACC controller (unsourced gains, safety supervisor, position clamp, message
  dropout). A CAV now follows the same IDM as a human driver; it uses the CAV time gap 0.6 s (CACC, Lecture 07
  p. 47) only when the vehicle ahead is also a CAV, because only then does it receive that vehicle's state over
  V2V. Behind a human driver or the zipper slot it keeps the human time gap. Lecture 05B pp. 28-31 realizes
  ACC with the IDM by changing its parameters, the time gap T being the main capacity factor.
- Check of the rewrite: with the platoon off, the new simulator reproduces the old one exactly for human drivers
  (same trajectories, same total delay) in three cases (T 1.0/1.2/0.8 s, ramp 700, seeds 281/284/284).
- Congestion is now judged at detector D1 (1,450 m, 150 m before the merge): **a 30-s interval is slow when its
  mean speed is below 11.1 m/s (40 km/h); the merge is congested when at least 4 consecutive intervals are
  slow (2 min).** On the 30 human runs of October (6 runs x 5 seeds) this agrees with the old trajectory
  definition in 30 of 30 runs; congested D1 intervals have about 55% occupancy, free-flow ones 8-10%.

## 2. CAV question and prediction (written 2026-11-15 00:57 UTC = 2026-11-14 16:57 PST, before any CAV run)

**Question.** At the demand of Run 4 (1,900 mainline + 700 ramp = 2,600 veh/h, 103% of the human capacity), how
large a CAV share p is needed so that the merge no longer becomes congested (D1 definition above), and when it
still becomes congested, are the stop-and-go waves weaker?

**Capacity with CAVs.** If each vehicle is a CAV with probability p, independently, a fraction p^2 of vehicles
are CAVs behind CAVs and use T = 0.6 s; the rest use the human T. Mixing the IDM equilibrium spacings gives

| p | 0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C(p), human T = 1.0 s [veh/h] | 2,519 | 2,527 | 2,550 | 2,589 | 2,646 | 2,724 | 2,826 | 2,956 | 3,124 | 3,339 | 3,619 |
| 2,600 / C(p) | 103% | 103% | 102% | 100% | 98% | 95% | 92% | 88% | 83% | 78% | 72% |
| C(p), human T = 1.2 s [veh/h] | 2,191 | 2,200 | 2,226 | 2,271 | 2,337 | 2,428 | 2,550 | 2,711 | 2,925 | 3,215 | 3,619 |
| 2,600 / C(p) | 119% | 118% | 117% | 115% | 111% | 107% | 102% | 96% | 89% | 81% | 72% |

Capacity grows slowly at first (only CAV pairs gain), as PATH simulations of CACC also report (capacity grows
quadratically with market penetration).

**Predictions (20 seeds, 281-300, per CAV share).**

1. Human T = 1.0 s: congestion in (nearly) every seed while demand is above C(p), i.e. p <= 0.3. Between 88% and
   100% of capacity (p = 0.4-0.6) congestion still happens in some seeds, because the human runs broke down at
   88% (Run 2, seed 284). At p >= 0.8 (83% or less) essentially no congestion.
2. Human T = 1.2 s (Run 6 demand): congestion in every seed for p <= 0.6, then falling; none at p = 1.0.
3. Waves: when congestion still forms, it still starts at the merge and its waves still move backward at about
   15 km/h, with a similar number of stops per queued vehicle, because the zipper (full stops) is unchanged. CAVs
   should lower the chance of a breakdown more than its severity.
4. No collisions (0 overlap steps) at any CAV share.

## 3. Results (2026-11-15, 20 seeds per case; `run_time_gap_sweep.py`, `run_cav_sweep.py`)

Human drivers only (D1 definition): share of runs congested = 0% (Run 1, 71% of C), 15% (Run 2, 88%), 0% (Run 3,
83%), 95% (Run 4, 103%), 0% (Run 5, 96%), 100% (Run 6, 119%). Seed 281 gives the same verdicts as in October
(Run 4: 99 vehicles waiting at 10 min). No collisions in 120 runs.

CAV share sweep, share of runs congested [%]:

| p | 0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| human T = 1.0 s | 95 | 90 | 90 | 75 | 80 | 30 | 20 | 15 | 10 | 5 | 5 |
| human T = 1.2 s | 100 | 100 | 100 | 100 | 100 | 100 | 80 | 30 | 15 | 10 | 5 |

- Vehicles waiting at 10 min (human T = 1.0 s): 102 at p = 0, 31 at p = 0.5, 8 at p = 1.0 (means over seeds).
- When a run is congested, the merge passes 1,470-1,670 veh/h at every p: the zipper's full stops, not the time
  gap, set the discharge.
- Stops per queued vehicle in congested runs rise with p: 4.1 (p = 0) to 6-8 (p >= 0.8) for human T = 1.0 s;
  1.4 to 6.2 for 1.2 s. Wave speed 14-17 km/h backward at every p.
- The congested runs at p >= 0.8 are seeds 284, 289 and 299. Seed 284 has a burst of 24 ramp arrivals in one minute
  (170-230 s; the mean is 11.7), just before the breakdown.
- No collisions in 440 runs; smallest gap 1.50 m (1.77 m without CAVs). Time step 0.05/0.2 s changes the base
  delay by -2.6%/+3.8% (`run_checks.py`).

Against the predictions:

1. Held in part. Congestion stays in 75-95% of runs while demand is at least 98% of C(p) (p <= 0.4) and drops
   steeply between p = 0.4 and 0.5. But it does not vanish: 5-10% of runs still break down at 72-83% of capacity.
2. Held up to p = 0.5 (100%) and 0.6 (80%); not zero at p = 1.0 (5%).
3. Wave speed held; the number of stops did not. With many CAVs, a queue that does form is more stop-and-go.
   Likely cause: the IDM becomes less stable as T shrinks, and our CAV model has no acceleration feedforward,
   which real CACC uses to stay string stable.
4. Held.

## 4. Basic TMC: ramp metering (2026-11-15, `run_tmc.py`, Run 4 demand, 20 seeds)

Settings: ALINEA r(k) = r(k-1) + K_R (target - o_D2(k)) every 30 s, K_R = 70 veh/h per % (Papageorgiou et al.
1991), rate bounds 240-900 veh/h (FHWA ATDM guide defaults), target 17% = occupancy at capacity of the human
IDM (k_c = 34.9 veh/km x 5 m = 17.4%); queue override to 900 veh/h when the ramp queue reaches 25 of 35; fallback
to the fixed rate when D2 data are missing. Fixed baselines: 600 veh/h (capacity 2,519 - mainline 1,900 = 619)
and 900 veh/h.

**Unfair first version found and fixed.** In the first runs a ramp vehicle rejected at a metered ramp waited 1 s
before checking again, while without a meter it checks every 0.1 s. With that rule, fixed meters at 900, 1,800 and
3,600 veh/h all gave 5% congested runs (vs. 95% without a meter), identical to each other: the benefit came from
the 1-s re-check, not from metering. Fixed: a rejected vehicle now checks again at the next step in every mode.
This also shows that **our breakdowns depend strongly on how often a waiting ramp driver re-checks the gap**
(a challenge for Section 4 of the report).

Results after the fix (mean over 20 seeds; delay includes waiting at the boundary and in the ramp queue):

| Controller | Congested, no CAVs | Delay [veh h], no CAVs | Ramp queue max | Not served | Congested, 50% CAVs | Delay, 50% CAVs |
|---|---|---|---|---|---|---|
| no meter | 95% | 10.3 +- 2.5 | 7.5 | 0 | 30% | 4.4 +- 2.7 |
| fixed 600 veh/h | 30% | 7.1 +- 2.4 | 29.1 | 2.1 | 0% | 4.9 +- 0.5 |
| fixed 900 veh/h | 90% | 9.0 +- 2.5 | 9.6 | 0 | 15% | 4.5 +- 2.4 |
| ALINEA 17% | 85% | 9.1 +- 2.5 | 9.6 | 0 | 15% | 4.4 +- 2.3 |
| ALINEA 15% | 60% | 8.1 +- 2.7 | 16.8 | 0 | 10% | 4.1 +- 2.0 |
| ALINEA 13% | 30% | 8.0 +- 2.9 | 26.2 | 0 | 5% | 4.4 +- 1.7 |
| ALINEA 13%, D2 lost at 5 min | 35% | 8.9 +- 3.8 | 27.0 | 2.5 | - | - |

- Metering helps when demand exceeds capacity: congestion 95% -> 30% and delay 10.3 -> 7-8 veh h, by holding ramp
  vehicles on the ramp.
- ALINEA with the target at the critical occupancy (17%) hardly acts: D2 stays near 15-17% before the breakdown.
  A target below critical (13%) cuts congestion to 30% without unserved vehicles; the fixed 600 veh/h meter does the
  same but leaves about 2 ramp vehicles per run unserved (ramp storage full).
- Fallback works: with D2 lost the meter switches to 600 veh/h; results stay close to ALINEA 13%.
- With 50% CAVs all controllers give similar delay (4.1-4.9 veh h); metering lowers the congested share (30% -> 0-15%).
- Note: the 15% and 13% targets were chosen on these same runs (no separate tuning data).
