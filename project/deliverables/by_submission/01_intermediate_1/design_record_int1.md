# Design record - Intermediate 1: proposal, interfaces, minimum simulation

Team: Seunghun Oh, Rocair (confirm official names/UIDs). Pathway: CAV (preliminary).
Companion files in this folder: `experiment_record.md` (pre-run predictions and results) and
`contribution_record_int1.md` (roles, vehicle traces, individual answers).

## 1. Problem and scope

**Question.** Does a braking disturbance fade, grow, or turn into a lasting queue near a freeway bottleneck?

**System boundary.** A one-lane freeway from x = 0 m to x = 2,500 m (positions increase downstream).
Vehicles enter at x = 0 (mainline, 1,500 veh/h) and at the on-ramp merge at x = 1,200 m (360 veh/h),
at constant spacing for the first 10 min, and leave at x = 2,500 m. A 12-vehicle platoon starts on the
road at 79 km/h. The bottleneck is the 300-m zone at 1,600-1,900 m, where drivers keep a longer time gap.
The ramp meter is off in Intermediate 1. The run lasts 15 min, so queues can clear after arrivals stop.

**First behavioral prediction** (written before the run; details in `experiment_record.md`): a single
braking event in free-flowing traffic fades as it passes back through the following vehicles, and the
demand of 1,860 veh/h, above the zone's 1,743 veh/h capacity, builds a queue in front of the zone that
clears after arrivals stop.

**Why the scope is small.** One lane, identical drivers, constant arrivals, one disturbance, one
bottleneck, no control. Each predicted number follows from the IDM equilibrium relations, and each
observed behavior can be traced to one equation and one code location.

## 2. Model and source-to-design table

Intelligent Driver Model (IDM), applied to every human driver at every 0.1-s step:

a = a_max [1 - (v/v0)^δ - (s*/s)²],  s* = s0 + v·T + v·Δv / (2√(a_max·b))

v = own speed [m/s]; s = bumper-to-bumper gap to the leader [m]; Δv = own speed - leader speed [m/s].
Code: `src/cavsim/core.py::idm_acceleration`; positions and speeds are updated in `FreewaySimulation._advance`.

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
| Bottleneck | T = 1.6 s for 1,600-1,900 m | method and value: Treiber, Hennecke & Helbing (2000), local increase of T (their Table 1 value); location and length are design choices | a stylized capacity drop, not a specific geometry |
| Entry and merge | admitted only if both gaps ≥ s0 and no vehicle must brake harder than b; ramp vehicle enters at its new leader's speed | design choice using only the IDM and b | one-point merge; see Section 6 |
| Time step | 0.1 s | design choice, checked at 0.05 s and 0.2 s | |

Capacity check from the equilibrium relation s_e(v) = (s0 + vT)/√(1 - (v/v0)^4), q = v/(s_e + l):
2,519 veh/h outside the zone, 1,743 veh/h inside it.

## 3. Interface draft

Units: seconds, metres, m/s, m/s². Origin: mainline entry, x = 0; positions increase downstream.
Missing values are left blank (NaN) and flagged; they are never replaced by 0. Vehicle ids are unique
and kept from entry to exit.

| Interface (file) | Fields, sampling | Valid bounds | Example row from the Int 1 run |
|---|---|---|---|
| Vehicle state (`trajectories.csv`) | time_s, vehicle_id, lane_id, position_m, speed_mps, acceleration_mps2, controller, equipped; every 0.5 s | 0 ≤ position_m ≤ 2,500; speed_mps ≥ 0 | `0.0, veh_0000, mainline_1, 105.0, 22.0, 0.0, human, False` |
| Observation (`observations.csv`) | sensor_id, interval_start_s, interval_end_s, count, mean_speed_mps, occupancy_pct, quality_flag; 30-s intervals, counts on (start, end] | count ≥ 0; 0 ≤ occupancy ≤ 100; mean speed blank if count = 0 | `D1, 300.0, 330.0, 13, 6.79, 31.6, ok` |
| Estimate/forecast | issue_time_s, target_time_s, segment_id, variable_name, units, method, estimated_state, predicted_value, quality_indicator | horizon 30 s | not used until Intermediate 3 |
| Control command (`control_commands.csv`) | issue_time_s, apply_time_s, actuator_id, action, value, units, lower_bound, upper_bound, fallback_active, reason, queue_estimate_veh | release rate 240-900 veh/h | `0.0, 0.0, ramp_meter_R1, release_rate, 900, veh/h, 240, 900, False, unmetered baseline, 0` |
| Evaluation record (`int1_results.json`) | scenario, metrics (delay, queues, unfinished vehicles, minimum gap, overlaps, hardest braking) | overlap_steps must be 0 | `"P6_unfinished_vehicles": 0, "P7_overlap_steps": 0` |

Each module runs on a small example: `python -m unittest discover -s tests -v` checks IDM free motion and
equilibrium, conservation on a 90-s case, the detector recount, and the snapshot interface.

## 4. Minimum runnable simulation

One command: `bash run_int1.sh` (creates the environment if needed, runs the unit tests, then
`run_int1.py`). Configuration: `configs/scenarios.json` (`int1_scenario`, `simulation`, `human_idm`).
Output: `outputs/int1/` (figures, CSV tables, `int1_results.json`). Live view: `python run_live.py`
opens the same scenario ("Intermediate 1 · human drivers only · ramp meter off").

## 5. First evidence

| | Predicted | Observed |
|---|---|---|
| Speed-drop ratio of the braking disturbance | 0.6-0.95 | 0.66: the disturbance fades |
| Where the queue starts | upstream of 1,600 m | 1,621 m, at 3.1 min |
| Vehicles stored / queue end | 18-39 / near the ramp | 24 / 1.32 km |
| Recovery | clears after arrivals stop | last slow vehicle at 13.2 min; none left |

Checks: conservation holds, no collisions, smallest gap 5.7 m, hardest braking 3.4 m/s², and results
change by < 3% at time steps of 0.05 s and 0.2 s. Not predicted correctly: the queue stayed smooth
instead of forming stop-and-go waves. Figures: `outputs/int1/time_space_all_vehicles.png`,
`disturbance_speed_traces.png`, `detectors_and_ramp_queue.png`.

## 6. Final pathways (preliminary) and limitations

- **CAV (preliminary choice).** It reuses this freeway directly, and the disturbance question above leads
  straight to the CAV question: can ACC/CACC vehicles make such disturbances fade faster without losing
  throughput? Confirmation is due at Intermediate 3.
- **Signal control (considered).** It would move the work to a supplied isolated intersection and a
  fixed-time baseline. That would reuse less of this freeway model and of its disturbance question.
- **Limitation: merge rule.** From minute 5 to 10 no ramp vehicle merges: it enters at the speed of a
  leader already slowing for the queue, so the fast follower would have to brake harder than b. This
  comes from our one-point merge, not from the IDM; to be revised in Intermediate 2.
- **Limitation: demand.** Arrivals stop abruptly at 10 min instead of tapering off.

## AI use and verification

AI assistance (Claude) was used to review the baseline code, draft code changes, compute the theoretical
values used in the predictions, and draft these documents. Checks performed: IDM parameter values were
compared with Table 1 of the original paper and with the textbook errata for Table 11.2; unit tests pass;
results were reproduced at three time steps; the pre-run predictions were recorded before the run and
are reported whether or not they held. Each team member answers the individual questions in
`contribution_record_int1.md` in their own words.

## References

1. Treiber, M., Hennecke, A., & Helbing, D. (2000). Congested traffic states in empirical observations and
   microscopic simulations. *Physical Review E*, 62, 1805-1824. https://doi.org/10.1103/PhysRevE.62.1805
2. Treiber, M., & Kesting, A. (2013). *Traffic Flow Dynamics: Data, Models and Simulation*. Springer.
   Chapter 11, Table 11.2 (with the authors' errata, traffic-flow-dynamics.org).
