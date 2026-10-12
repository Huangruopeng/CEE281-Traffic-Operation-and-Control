# Design record - Intermediate 1: proposal, interfaces, minimum simulation

Team: Seunghun Oh, Ruopeng (confirm official names/UIDs). Pathway: CAV (preliminary).
Companion files in this folder: `experiment_record.md` (pre-run predictions and results of every run) and
`contribution_record_int1.md` (roles, vehicle traces, individual answers).

## 1. Problem and scope

**Questions.** (1) Does a single braking disturbance fade or grow as it passes back through the following
vehicles? (2) When on-ramp vehicles merge into a busy mainline, how far back does the slowdown spread, and
how long does it last?

**System boundary.** A one-lane freeway from x = 0 m to x = 2,500 m (positions increase downstream).
For the first 10 min, vehicles enter at x = 0 (mainline, 1,900 veh/h on average) and at the on-ramp merge
at x = 1,600 m (700 veh/h); arrival times are random (Poisson, one seed: 281). All vehicles leave at
x = 2,500 m. The **merge is the only bottleneck**: the mainline alone uses 75% of the lane capacity
(2,519 veh/h), mainline plus ramp would need 103%. A 12-vehicle platoon starts on the road at 79 km/h, and
one of its vehicles brakes once. The ramp stores up to 35 vehicles; the ramp meter is off. The run lasts
15 min, so queues can clear after arrivals stop. Detectors: D1 at 1,450 m (before the merge), D2 at 2,050 m.

**First behavioral prediction** (written before the run; details in `experiment_record.md`): the braking
disturbance fades; without ramp traffic no queue forms; with ramp traffic a queue forms just upstream of
the merge, spreads back about 0.5-0.75 km, keeps the ramp queue at about 10 vehicles or fewer, and clears
after arrivals stop. The merge rule needed seven revisions before it behaved as intended; each revision is
recorded with its prediction and result.

**Why the scope is small.** One lane, identical drivers, one disturbance, one bottleneck (the merge), no
control. Each observed behavior can be traced to one equation and one code location.

## 2. Model and source-to-design table

Intelligent Driver Model (IDM), applied to every human driver at every 0.1-s step:

a = a_max [1 - (v/v0)^δ - (s*/s)²],  s* = s0 + v·T + v·Δv / (2√(a_max·b))

v = own speed [m/s]; s = bumper-to-bumper gap to the leader [m]; Δv = own speed - leader speed [m/s].
Code: `src/cavsim/core.py::idm_acceleration`; positions and speeds are updated in `FreewaySimulation._advance`.

**Merge rule** (code: `_process_arrivals`, `_merge_safe_decel`, `_zipper_leader`). The front ramp vehicle
enters at the merge point at its new leader's speed, but at most 89 km/h. It may enter only if both gaps are
at least s0 and its new follower would not have to brake harder than the merge limit, which grows as the
follower gets slower (4 m/s² at the desired speed, 17 m/s² at standstill). In slow traffic (below 40 km/h)
mainline drivers take turns with the ramp (zipper merge): the first mainline vehicle within 100 m before
the merge stops for an imaginary standing car at the merge point, which leaves one slot; after a ramp
vehicle enters, the next turn belongs to the mainline.

| Choice | Value | Source | Limitation |
|---|---|---|---|
| Model equations | as above, s1 = 0 | Treiber, Hennecke & Helbing (2000) | no reaction delay; identical drivers |
| Desired speed v0 | 33.33 m/s (120 km/h) | Treiber & Kesting (2013), Table 11.2, cars on freeway | not a specific road's speed limit |
| Time gap T | 1.0 s | same table | |
| Minimum gap s0 | 2 m | same table | |
| Maximum acceleration a_max | 1.0 m/s² | same table | |
| Comfortable deceleration b | 1.5 m/s² | same table | IDM can exceed b in critical situations |
| Exponent δ | 4 | same table | |
| Vehicle length | 5 m | Treiber, Hennecke & Helbing (2000), Table 1 | cars only |
| Demand | 1,900 + 700 veh/h for 10 min, Poisson arrivals | design choice: mainline 75%, total 103% of capacity; random arrivals at the instructor's request | one seed; arrivals stop abruptly at 10 min |
| Merge location | 1,600 m | design choice | one merge point, no acceleration lane |
| Merge speed cap | 24.6 m/s (89 km/h) | AASHTO (2004), Exhibit 10-70: speed reached at the merge on a 75-mph highway | |
| Merge braking limit | 4 m/s² at v0, rising linearly to 17 m/s² at standstill | safety criterion of MOBIL (Kesting, Treiber & Helbing 2007); values from the MOBIL code on traffic-simulation.de | |
| Zipper merge | below 40 km/h, first vehicle within 100 m | design choice (40 km/h is also our "congested" threshold) | yielding vehicles stop completely; see Section 6 |
| Human braking cap | 9 m/s² | traffic-simulation.de, MOBIL page ("maximum deceleration of about 9 m/s²") | collisions are counted, not prevented |
| Time step | 0.1 s | design choice, checked at 0.05 s and 0.2 s | |

Capacity check from the equilibrium relation s_e(v) = (s0 + vT)/√(1 - (v/v0)^4), q = v/(s_e + l):
2,519 veh/h at 72 km/h.

## 3. Interface draft

Units: seconds, metres, m/s, m/s². Origin: mainline entry, x = 0; positions increase downstream.
Missing values are left blank (NaN) and flagged; they are never replaced by 0. Vehicle ids are unique
and kept from entry to exit.

| Interface (file) | Fields, sampling | Valid bounds | Example row from the Int 1 run |
|---|---|---|---|
| Vehicle state (`trajectories.csv`) | time_s, vehicle_id, lane_id, position_m, speed_mps, acceleration_mps2, controller, equipped; every 0.5 s | 0 ≤ position_m ≤ 2,500; speed_mps ≥ 0 | `0.0, veh_0000, mainline_1, 105.0, 22.0, 0.0, human, False` |
| Observation (`observations.csv`) | sensor_id, interval_start_s, interval_end_s, count, mean_speed_mps, occupancy_pct, quality_flag; 30-s intervals, counts on (start, end] | count ≥ 0; 0 ≤ occupancy ≤ 100; mean speed blank if count = 0 | `D1, 420.0, 450.0, 6, 1.84, 56.5, ok` (inside the queue) |
| Estimate/forecast | issue_time_s, target_time_s, segment_id, variable_name, units, method, estimated_state, predicted_value, quality_indicator | horizon 30 s | not used until Intermediate 3 |
| Control command (`control_commands.csv`) | issue_time_s, apply_time_s, actuator_id, action, value, units, lower_bound, upper_bound, fallback_active, reason, queue_estimate_veh | release rate 240-900 veh/h | `0.0, 0.0, ramp_meter_R1, release_rate, 900, veh/h, 240, 900, False, unmetered baseline, 0` (meter off: the rate is logged but not applied) |
| Evaluation record (`int1_results.json`) | scenario, metrics (delay, queues, unfinished vehicles, minimum gap, overlaps, hardest braking) | overlap_steps must be 0 | `"P6_unfinished_vehicles": 0, "P7_overlap_steps": 0` |

Each module runs on a small example: `python -m unittest discover -s tests -v` checks IDM free motion and
equilibrium, conservation on a 90-s case, the detector recount, and the snapshot interface.

## 4. Minimum runnable simulation

One command: `bash run_int1.sh` (creates the environment if needed, runs the unit tests, then
`run_int1.py`). Configuration: `configs/scenarios.json` (`int1_scenario`, `simulation`, `human_idm`).
Output: `outputs/int1/` (figures, CSV tables, `int1_results.json`). The script also runs a control case
without ramp traffic. Live view: `python run_live.py` opens the same scenario.

## 5. First evidence

| | Predicted | Observed |
|---|---|---|
| Speed-drop ratio of the braking disturbance | 0.6-0.95 | 0.66: the disturbance fades |
| Queue without ramp traffic | none | none, so the merge causes the queue |
| Where the queue starts | just upstream of 1,600 m | at the merge (1,600 m), at 5.2 min |
| How far it spreads | 40-55 vehicles, 0.5-0.75 km | 103 vehicles, about 1 km (tail at 0.61 km); D1 below 40 km/h at 7 min |
| Ramp queue | about 10 or fewer | at most 7, never full |
| Recovery | clears after arrivals stop | last slow vehicle at 12.9 min; none left |

Inside the queue traffic moves in stop-and-go waves: the 129 vehicles that slowed below 5 km/h there came
to a stop 3.6 times each on average (up to 8). Checks: conservation holds, no collisions, smallest gap
1.8 m, hardest braking 9.0 m/s² (the cap), and the ratio and delay change by < 4% at time steps of 0.05 s
and 0.2 s. Not predicted correctly: the queue is about twice as large as predicted (Section 6). Figures:
`outputs/int1/time_space_all_vehicles.png`, `disturbance_speed_traces.png`, `detectors_and_ramp_queue.png`.

## 6. Final pathways (preliminary) and limitations

- **CAV (preliminary choice).** It reuses this freeway directly, and both questions above lead to the CAV
  question: can ACC/CACC vehicles make disturbances fade faster and damp the stop-and-go waves at the
  merge without losing throughput? Confirmation is due at Intermediate 3.
- **Signal control (considered).** It would move the work to a supplied isolated intersection and a
  fixed-time baseline. That would reuse less of this freeway model and of its disturbance question.
- **Limitation: zipper rule.** Every yielding vehicle stops completely, so during the jam the merge
  passes only about 1,500 veh/h, 40% below the lane capacity. This is why the queue is larger than
  predicted. A real merge probably loses less, because drivers adjust their speed earlier; we have not
  checked this against data.
- **Limitation: demand.** One random seed only; arrivals stop abruptly at 10 min instead of tapering off.
- **Limitation: sources.** The merge rule needs three sources beyond the two IDM references (AASHTO,
  MOBIL, traffic-simulation.de), and the zipper thresholds are our own choices.

## AI use and verification

AI assistance (Claude) was used to review the baseline code, draft code changes, compute the theoretical
values used in the predictions, and draft these documents. Checks performed: IDM parameter values were
compared with Table 1 of the original paper and with the textbook errata for Table 11.2; unit tests pass;
results were reproduced at three time steps; the pre-run predictions were recorded before each run and
are reported whether or not they held, including the failed merge rules. Each team member answers the
individual questions in `contribution_record_int1.md` in their own words.

## References

1. Treiber, M., Hennecke, A., & Helbing, D. (2000). Congested traffic states in empirical observations and
   microscopic simulations. *Physical Review E*, 62, 1805-1824. https://doi.org/10.1103/PhysRevE.62.1805
2. Treiber, M., & Kesting, A. (2013). *Traffic Flow Dynamics: Data, Models and Simulation*. Springer.
   Chapter 11, Table 11.2 (with the authors' errata, traffic-flow-dynamics.org).
3. Kesting, A., Treiber, M., & Helbing, D. (2007). General lane-changing model MOBIL for car-following
   models. *Transportation Research Record*, 1999, 86-94. https://doi.org/10.3141/1999-10
4. AASHTO (2004). *A Policy on Geometric Design of Highways and Streets* (5th ed.), Exhibit 10-70.
5. Treiber, M. traffic-simulation.de, MOBIL lane-change model page and source code (accessed 2026-10-12).
