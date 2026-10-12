# Contribution record - Intermediate 1

Proposed split (to be confirmed by both team members). Each person owns one coherent part, can run it
alone, and explains one test of the other person's interface.

## Seunghun Oh - vehicle dynamics and numerical verification

| | |
|---|---|
| Component | IDM car following and the vehicle update |
| Code location | `src/cavsim/core.py`: `idm_acceleration`, human branch of `FreewaySimulation._compute_commands`, `FreewaySimulation._advance` (stop within a step, 9 m/s² braking cap, overlap counting) |
| Interface owned | Vehicle state (`trajectories.csv`); evaluation metrics minimum gap, `overlap_steps`, hardest braking |
| Tests owned | `test_idm_free_motion`, `test_idm_equilibrium`, conservation part of `test_minimum_case_conservation_and_detector_audit`, time-step check in `run_int1.py` (0.05 / 0.1 / 0.2 s) |
| Conclusion owned | Prediction 1: the free-flow braking disturbance fades (ratio 0.66); a 0.1-s step is adequate |
| Planned next tests | where the stop-and-go waves in the merge queue start and how they travel back; time-step check of the queue dynamics |
| Vehicle traced | `veh_0358` (ramp vehicle): reaches the ramp at 472 s, waits 10 s, merges at 482 s at about 5 m/s into the slot that mainline vehicle `veh_0254` left by braking (zipper), then follows the IDM to the exit at 525 s. Show its row history in `trajectories.csv` and the ramp queue in `queues.csv` |
| Test of partner's interface explained | detector recount: counts in `observations.csv` equal the vehicle crossings logged in `crossings.csv` (`audit_detector_counts` in `observation.py`) |

## Ruopeng - boundaries, merge and observations

| | |
|---|---|
| Component | random arrivals, mainline entry, ramp storage and the merge rule (speed cap, merge braking limit, zipper), detectors, live view |
| Code location | `src/cavsim/core.py`: `_demand_schedules`, `_process_arrivals`, `_insertion_is_safe`, `_merge_safe_decel`, `_zipper_leader`, `DetectorAccumulator`; `src/cavsim/observation.py`; `live_visualization/` |
| Interface owned | Observation (`observations.csv`); control command (`control_commands.csv`) |
| Tests owned | detector-recount part of `test_minimum_case_conservation_and_detector_audit`, `test_live_step_and_snapshot_interface`, ramp storage/overflow accounting, the control run without ramp traffic in `run_int1.py` |
| Conclusion owned | Prediction 2: the merge is the bottleneck. Without ramp traffic no queue forms; with it, a mainline queue starts at the merge, spreads about 1 km back and clears after arrivals stop, while the zipper keeps the ramp queue at 7 or fewer |
| Planned next tests | a zipper rule in which yielding vehicles slow down instead of stopping (the merge now loses 40% of its capacity); a detector defect test (missing intervals) |
| Vehicle traced | `veh_0010`, the braking platoon vehicle: brakes at -2.5 m/s² from 8 s to 12 s; show how the 8 vehicles behind it slow down less (`disturbance_speed_traces.png`) |
| Test of partner's interface explained | vehicle conservation: generated = exited + vehicles still in the system or in a queue (`run()` metrics, `P7_conservation_ok`) |

## Individual check (each person answers in their own words, with the run, the code and the evidence)

**1. Which term or assumption in the model most affects whether the disturbance grows or decays? Why?**
Evidence to bring: the IDM equation in `idm_acceleration` (terms with T and a_max); speed-drop ratio 0.66;
the linear stability result in `experiment_record.md` (unstable below about 72 km/h for T = 1.0 s).

- Seunghun: I think the key part of IDM is how a car responds when the gap to the car ahead shrinks. In our runs, stronger braking by the lead car caused a larger speed drop farther back in the platoon: the speed-drop ratio rose from 0.66 with a −2.5 m/s² brake to 0.73 with a −3.5 m/s² brake. Both ratios are below 1, though, so the disturbance still faded as it moved through the platoon.
- Ruopeng: I think the desired time gap `T` and the operating speed matter most. `T` enters the desired gap through `vT`, so it changes how strongly a driver responds to a shrinking gap. At 79 km/h with `T = 1.0 s`, the platoon is above the approximate 72-km/h stability boundary, and the measured ratio of 0.66 shows that the disturbance fades. A larger `T` gives more following margin, but it also lowers capacity, which is why `T = 1.6 s` creates the bottleneck queue.

**2. Why is the selected time step appropriate, and what failure would make you reduce it?**
Evidence to bring: `P8_timestep` in `outputs/int1/int1_results.json` (0.05 / 0.1 / 0.2 s).

- Seunghun: A 0.1 s time step seems fine for this setup. When I reduced it to 0.05 s, the speed-drop ratio changed by 0.4% and total delay by 2.4%. I would use a smaller step if cars started overlapping, their motion showed sudden numerical jumps, or halving the step changed the results substantially.
- Ruopeng: A 0.1-s step gives 40 updates during the four-second brake and 24 between mainline arrivals. Across 0.05, 0.1, and 0.2 s, the amplification ratio stays between 0.655 and 0.664, the minimum gap stays near 5.7 m, and no overlaps occur. I would reduce the step if halving it changed the queue location, merge decisions, detector counts, or produced overlaps. The one-interval D1 shift at 0.2 s does not change the conclusion.

**3. Pick one parameter: why is its value plausible, what source supports it, and how would a larger value change the result?**
Evidence to bring: the source table in `design_record_int1.md`; for T, the lane capacity of 2,519 veh/h
with T = 1.0 s versus 1,743 veh/h with T = 1.6 s.

- Seunghun: I used T = 1.0 s, based on the freeway-car values in Table 11.2 of Treiber and Kesting (2013). At 100 km/h, the vT part of the desired gap is about 28 m, which gives me a sense of what that setting means in practice. Increasing T means cars leave more space. The IDM capacity formula gives 2,519 veh/h at T = 1.0 s but only 1,743 veh/h at T = 1.6 s. In our merge scenario, that lower capacity would leave even more of the same demand unserved, so the queue would start earlier and grow longer.
- Ruopeng: I selected the comfortable-deceleration magnitude `b = 1.5 m/s²`, supported by Treiber and Kesting (2013), Table 11.2. It represents normal comfortable braking rather than an emergency limit. In our merge rule, a larger `b` would allow a follower to accept stronger braking, so more ramp vehicles could enter and the ramp queue might shrink. However, it could also create tighter merges, harder mainline braking, and smaller gaps. This parameter therefore exposes a tradeoff between ramp storage and mainline stability.

## Changes made in response to feedback

(none yet)
