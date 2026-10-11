# Traffic Engineering Primer for This Project

This is not a complete traffic engineering textbook. It is the shortest learning path needed to understand, run, explain, and defend this project. Every concept below is connected to the actual implementation and outputs.

## 1. The overall mental model

Think of the project as six layers:

1. **Physical system:** road, vehicles, on-ramp, bottleneck, and queues.
2. **Behavior model:** a human-driver model or automated controller selects acceleration.
3. **Simulation:** vehicle speed and position are updated every `0.1 s`.
4. **Observation:** virtual detectors provide limited count, speed, and occupancy measurements.
5. **Control:** the ramp meter or CAV controller acts only on information available at that time.
6. **Evaluation:** full simulator truth is used after the run to calculate delay, gaps, and disturbance amplification.

The most important rule is: **the controller cannot look into the future; the evaluator may use complete truth only after the run.**

## 2. Fundamental traffic variables

### 2.1 Position, speed, and acceleration

- Position `x`, measured in metres.
- Speed `v`, measured in metres per second. `1 m/s = 3.6 km/h`.
- Acceleration `a`, measured in metres per second squared. A negative value means deceleration.

Each simulation time step approximately applies:

```text
v_new = max(0, v_old + a * dt)
x_new = x_old + v_old * dt + 0.5 * a * dt^2
```

The project uses `dt = 0.1 s`. A smaller time step usually gives a closer approximation to continuous motion but costs more computation. Time-step sensitivity is therefore required to show that the conclusion is not a numerical artifact.

### 2.2 Three measures of vehicle separation

- **Net gap:** distance from the rear of the leader to the front of the follower.
- **Spacing:** corresponding points on consecutive vehicles; here it is vehicle length plus net gap.
- **Time headway:** time between consecutive vehicles passing the same point. Under simplified steady conditions, it is approximately spacing divided by speed.

Vehicle length is `5 m`. With consistent vehicle position definitions, the code uses:

```text
net gap = x_leader - x_follower - 5 m
```

For example, a `20 m` net gap and a `5 m` vehicle produce `25 m` spacing. At `20 m/s`, spacing divided by speed is approximately `1.25 s`.

Do not confuse actual net gap with the controller's desired time-gap parameter. The first is a measured state; the second defines a control target.

### 2.3 Flow, speed, and density

- **Flow** `q`: vehicles passing a point per unit time, commonly veh/h.
- **Mean speed** `v`: commonly km/h or m/s.
- **Density** `k`: vehicles per unit road length, commonly veh/km.

When units and averaging definitions are compatible:

```text
q = k * v
```

Example: 15 vehicles in 30 seconds give `q = 15 / 30 * 3600 = 1800 veh/h`. If mean speed is `90 km/h`, the corresponding density is approximately `1800 / 90 = 20 veh/km`.

This is a macroscopic average relationship. It does not mean that every vehicle behaves identically, and it must not be used with inconsistent units.

## 3. Bottlenecks, capacity, and queues

A **bottleneck** is a location with lower service ability, such as a speed reduction, lane drop, or merge conflict. This project reduces desired speed from `30 m/s` to `18 m/s` between `1600 m` and `1900 m` to create a simplified bottleneck.

When arrival rate remains above departure or service rate, vehicles accumulate:

```text
queue change = arrivals - departures
```

If 30 vehicles arrive and 24 depart, the queue grows by 6 vehicles. Counting only exited vehicles would hide vehicles still waiting at the boundary. The project therefore records residual queues, unmet demand, and ramp overflow.

**Capacity** is the maximum sustainable service flow under specified conditions. This project does not claim to calibrate the exact capacity of a real freeway. It compares control strategies in one controlled simulation environment.

## 4. Reading a time-space trajectory plot

In a time-space diagram, time is usually on the horizontal axis and position on the vertical axis:

- Line slope represents speed.
- A steeper line means faster travel; a flatter line means slower travel.
- Many lines becoming flatter and closer together usually indicate a queue or traffic wave.
- Lines should not cross in this single-lane model. Crossing can indicate overtaking, ordering errors, or a collision.

Use [`../outputs/plots/03_time_space_trajectories.png`](../outputs/plots/03_time_space_trajectories.png) to inspect the braking disturbance and bottleneck response.

## 5. Human car following: IDM

### 5.1 What the model does

The Intelligent Driver Model (IDM) calculates acceleration from ego speed, net gap, closing speed, and desired speed. It is a behavioral model, not a future-trajectory optimizer.

The implemented form is:

```text
a_IDM = a_max * [1 - (v/v0)^delta - (s_star/s)^2]

s_star = s0 + max(0, v*T + v*delta_v/(2*sqrt(a_max*b)))
```

Definitions:

- `v`: ego speed.
- `v0`: desired free-flow speed.
- `s`: actual net gap.
- `s0`: desired standstill gap.
- `T`: desired time gap.
- `delta_v = v_ego - v_leader`: closing speed; positive means the ego vehicle is approaching the leader.
- `a_max`: maximum comfortable acceleration.
- `b`: comfortable-deceleration parameter.
- `delta`: free-flow acceleration exponent.

Interpretation:

- With no leader and low speed, acceleration approaches `a_max`.
- As speed approaches `v0`, the free-flow acceleration term approaches zero.
- A small gap or rapid approach makes `(s_star/s)^2` large, producing deceleration.

Parameters are in [`../configs/scenarios.json`](../configs/scenarios.json). The implementation is `src/cavsim/core.py::idm_acceleration`.

### 5.2 Why two minimum checks matter

- **Free motion:** without a leader and at zero speed, the model should request its maximum acceleration parameter.
- **Equilibrium:** at a suitable steady following gap and equal speeds, acceleration should be approximately zero.

These tests verify that the equation was translated correctly. They do not show that the parameters represent a particular real freeway.

## 6. Virtual detectors and occupancy

A road detector observes vehicles crossing or occupying its detection area. It does not automatically know every vehicle's full state.

Every 30 seconds, this project reports:

- `count`: vehicles crossing during the interval.
- `mean_speed_mps`: mean crossing speed when at least one vehicle crosses.
- `occupancy_pct`: time-mean fraction of a 50-m detector zone covered by 5-m vehicles.
- `quality_flag`: normal or missing-data condition.

If no vehicle crosses during an interval, mean speed should remain missing rather than being set to zero. Zero speed means a stopped vehicle was measured; missing speed means no valid speed was available.

The detector audit independently recounts an exact crossing-event log using identical interval boundaries. All 10 sampled intervals have zero count error.

## 7. Conservation and correctness

An open-road simulation must account for every generated vehicle. Conceptually:

```text
generated = exited + active/on-road + waiting/unmet + overflow
```

If the identity fails, possible causes include:

- deleting a vehicle twice at an exit;
- silently dropping arrivals when storage is full;
- counting a ramp vehicle twice when it joins the mainline;
- failing to count residual vehicles at the end of the run.

Passing conservation proves only that vehicles did not disappear. It does not prove that the driving behavior is realistic.

## 8. Estimation, forecasting, and error

### 8.1 Three different concepts

- **Observation:** limited data directly reported by a sensor.
- **Estimation:** inference of a current state from limited or noisy data.
- **Forecast:** prediction of a specified future quantity at a declared horizon.

This project forecasts the vehicle count in the next 30-second interval.

### 8.2 Three-interval moving average

```text
forecast_next = mean(last 3 observed counts)
```

This is a simple, interpretable baseline. A more sophisticated method should be compared against a credible simple alternative.

### 8.3 Exponential smoothing

```text
state_t = alpha * observation_t + (1-alpha) * state_(t-1)
forecast_(t+1) = state_t
```

- Larger `alpha` emphasizes recent data and reacts faster but may follow noise.
- Smaller `alpha` is smoother but responds more slowly.

The project uses only the first-half development period to select `alpha`, then scores the held-out second-half evaluation period. Tuning and reporting performance on the same evaluation data would create optimistic bias.

### 8.4 Mean absolute error

```text
MAE = mean(abs(prediction - actual))
```

The project unit is vehicles per 30-second interval. With complete observations, exponential-smoothing MAE is approximately `1.820`, compared with `2.311` for the moving average. This means smoothing performs better on this held-out series; it does not prove universal superiority.

When every fifth interval is missing, smoothing MAE decreases to approximately `1.618`. The correct interpretation is that this deterministic missingness pattern happened to skip some harmful updates. It is not evidence that missing data improve forecasting.

## 9. The TMC and closed-loop control

The Traffic Management Center (TMC) is a logical feedback loop:

```text
observe -> estimate -> predict -> decide -> act -> evaluate
```

The ramp meter controls the rate at which vehicles are released from the on-ramp. The project compares:

- **Unmetered:** approximately unrestricted release.
- **Fixed:** constant `480 veh/h` release.
- **ALINEA-like feedback:** rate updated from downstream occupancy error.

The simplified update is:

```text
r_new = clip(r_old + K * (occupancy_target - occupancy_measured), r_min, r_max)
```

If downstream occupancy exceeds the target, the error is negative and the release rate decreases. If the ramp queue approaches storage capacity, a storage override raises the release rate to reduce spillback risk.

The feedback loop is functional and bounded but does not outperform unmetered release in the lightly constrained nominal case. This is a valid negative result: the target, gain, detector location, or traffic condition requires revision.

## 10. ACC and CACC

### 10.1 ACC

Adaptive Cruise Control uses locally measured:

- ego speed `v`;
- net gap `s`;
- relative speed `v_leader - v_ego`.

The desired net gap follows a constant-time-headway rule:

```text
desired_gap = standstill_gap + headway * ego_speed
spacing_error = actual_gap - desired_gap
```

The project command can be summarized as:

```text
speed_cmd = k_speed * (desired_speed - ego_speed)
gap_cmd   = kp * spacing_error + kd * (leader_speed - ego_speed)
u_ACC     = clip(min(speed_cmd, gap_cmd), -4, 2)
```

Selecting the smaller command prevents the vehicle from pursuing road speed when doing so would violate its following objective.

### 10.2 CACC

Cooperative ACC adds one communication term to the same local controller:

```text
gap_cmd_CACC = gap_cmd_ACC + 0.8 * delayed_predecessor_acceleration
```

The result still passes through speed limiting and `[-4, 2] m/s2` command bounds. The intuition is that when the leader begins braking, the follower can react to the message before the local gap changes substantially.

Communication uses only delayed acceleration from the immediate equipped predecessor. The controller falls back to ACC when:

- the predecessor is human-driven;
- a packet is dropped;
- no suitable message exists; or
- message age exceeds `1.0 s`.

This state is logged as `ACC_fallback`. The controller never reads the future disturbance schedule or full future trajectory.

### 10.3 Equipment penetration

Equipment penetration is the proportion of ACC/CACC-equipped vehicles:

- `0%`: human baseline.
- `50%`: mixed traffic.
- `100%`: fully equipped traffic.

Higher penetration does not guarantee monotonic improvement in every metric. In this project, 100% ACC has low delay but many hard-braking events, so one favorable metric is insufficient.

## 11. Three safety layers

The project does not resize visual vehicles to conceal overlap. Motion safety has three layers:

1. **Nominal controller:** IDM, ACC, or CACC produces an ordinary acceleration command.
2. **Safety supervisor:** predicted next-step clearance and differential stopping distance are checked. Bounded immediate braking is applied if the command would consume the `2.0 m` physical net-gap floor.
3. **Numerical invariant:** a final integration backstop prevents discrete numerical penetration and is counted separately. It activates zero times in all 12 final scenarios.

Safety-supervisor activations with zero numerical-guard activations are meaningful because control acts before any position correction is required.

This is still not real-world safety certification. A production assessment would need sensor error, actuator faults, road friction, lateral conflict, driver behavior, and vehicle testing.

## 12. Project evaluation metrics

### 12.1 Throughput

```text
throughput = exited vehicles / simulation duration
```

The result is converted to veh/h. Throughput alone can be misleading if an entry queue is ignored.

### 12.2 Total delay

Delay accumulates when a vehicle travels below its local desired speed, and entry waiting time is included. The final total is divided by 3600 and reported in veh-h. One veh-h can mean one vehicle delayed for one hour or 60 vehicles each delayed for one minute.

### 12.3 Minimum gap

The smallest bumper-to-bumper net gap observed during the simulation. It is a simulated geometric indicator, not a collision probability.

### 12.4 Hard-braking events

An event is counted when acceleration crosses into `< -3.0 m/s2`. This is a behavior and comfort surrogate, not a crash count.

### 12.5 Disturbance amplification

The project calculates leader speed loss and the maximum speed loss among following vehicles:

```text
amplification = maximum follower speed loss / leader speed loss
```

- `< 1`: the disturbance generally decays downstream.
- `= 1`: it remains approximately unchanged.
- `> 1`: at least one follower loses more speed than the disturbed leader.

The human baseline is already below one, so the project cannot claim that CACC beats human driving on this metric. The appropriate causal comparison is matched ACC versus CACC because communication feedforward is their only intended controller difference.

### 12.6 Residual and unmet demand

Vehicles still unfinished at the end of the simulation must be reported. Under high demand, CACC-50 exits 377 vehicles and the human case exits 347, but unfinished and overflow counts must also be inspected.

## 13. Fair experimental design

Except for the studied variable, controller comparisons should use:

- identical arrivals and initial vehicles;
- identical demand, bottleneck, and ramp logic;
- identical disturbance timing and strength;
- identical duration, time step, and metric definitions;
- the same seed or paired seeds when randomness is present.

The key ablation is:

```text
ACC:  no predecessor-acceleration feedforward
CACC: same local controller + delayed predecessor acceleration
```

The ACC/CACC difference can therefore be reasonably attributed to the communication term. Comparing human driving with CACC changes several mechanisms at once and cannot isolate communication by itself.

Write a prediction before running each experiment. If evidence contradicts the prediction, preserve and explain it. The engineering goal is a credible conclusion, not a collection of favorable plots.

## 14. Interpreting the final result

The nominal matched comparison at 50% penetration is:

| Metric | ACC-50 | CACC-50 | Interpretation |
|---|---:|---:|---|
| Throughput | 1288 veh/h | 1288 veh/h | Unchanged |
| Total delay | 1.700 veh-h | 1.947 veh-h | CACC increases delay by 14.6% |
| Amplification | 0.722 | 0.631 | CACC reduces amplification by 12.5% |
| Minimum gap | 4.670 m | 5.203 m | CACC increases minimum gap by 11.4% |
| Hard braking | 80 | 80 | No improvement |

Compared with the human baseline, CACC has lower delay, but human driving has lower amplification and fewer hard-braking events. It is therefore incorrect to say that CACC is uniformly better.

With degraded communication, CACC-50 delay, amplification, and hard braking worsen; fallback keeps commands bounded. Under high demand, CACC completes more trips and reduces delay, but hard braking remains higher than for human driving.

The final decision is:

> Predecessor-acceleration communication has incremental value over matched ACC, but current tuning and model evidence do not support direct adoption. The next design cycle needs retuning, multiple stochastic conditions, and measured-trajectory validation.

## 15. Verification, calibration, and validation

- **Verification:** did the code correctly implement the design? Examples include analytical equilibrium, conservation, detector recounting, and time-step sensitivity.
- **Calibration:** use data to choose parameters for a particular road, driver population, or vehicle.
- **Validation:** test predictive performance on independent real data not used for calibration.

This project has substantial verification but no field-trajectory calibration or validation. Say that the model passed simulation checks, not that real-road performance was proven.

## 16. Explaining one decision-trace row

Read one row in this order:

1. `issue_time_s`: when was the decision made?
2. `measured_ego_speed_mps`: how fast was the vehicle?
3. `measured_gap_m`: what was the measured net gap?
4. `measured_relative_speed_mps`: was the leader pulling away or being approached?
5. `communicated_predecessor_accel_mps2`: was delayed acceleration available?
6. `message_valid/message_age_s`: was the message valid, and how old was it?
7. `command_mps2`: what bounded command was issued?
8. `fallback_state`: normal CACC, ACC fallback, or safety override?

A concise defense is: the controller used only contemporaneous local kinematics and the allowed delayed message; future trajectories were used only for post-run evaluation.

## 17. Four-stage learning plan

### Before Intermediate 1

- Learn Sections 1-5.
- Draw leader and follower vehicles and label `x`, `v`, `a`, and net gap.
- Explain the two minimum IDM checks.
- Locate model, configuration, and interface files.

### Before Intermediate 2

- Learn Sections 6-7 and 12-13.
- Convert a 30-second count to veh/h.
- Read a time-space plot.
- Explain conservation, detector audit, and time-step sensitivity.

### Before Intermediate 3

- Learn Sections 8-10.
- Calculate a moving average, one exponential-smoothing update, and MAE.
- Explain the TMC loop and ALINEA-like update.
- Identify the single additional CACC input relative to ACC.

### Before the final presentation

- Learn Sections 11 and 14-16.
- Explain one decision-trace row without reading a script.
- Present both favorable and unfavorable results.
- Defend the `revise before adoption` decision.

## 18. Self-test questions and short answers

Answer aloud before reading each answer.

**1. Fifteen vehicles pass in 30 seconds. What is the flow?**  
`15/30*3600 = 1800 veh/h`.

**2. What is the difference between net gap and spacing?**  
Spacing includes one vehicle length; net gap is bumper-to-bumper clearance.

**3. What does a flatter line mean on a time-space plot?**  
Position changes more slowly with time, so vehicle speed is lower.

**4. Why is IDM not ACC?**  
IDM is a continuous human-following behavior model. ACC is a controller with defined measurements, a spacing objective, gains, command bounds, and actuator response.

**5. What does CACC add to ACC?**  
Delayed predecessor-acceleration feedforward from the immediate equipped leader; invalid communication triggers ACC fallback.

**6. Why is CACC-versus-ACC comparison essential?**  
It isolates the value of communication. Human-versus-CACC comparison changes several mechanisms simultaneously.

**7. Does equal throughput imply equal performance?**  
No. Delay, residual queues, disturbance amplification, gaps, and braking behavior also matter.

**8. Does a safety-supervisor activation mean a collision occurred?**  
No. It means the controller intervened early. Zero final numerical-guard activations show that no post-integration correction was needed.

**9. Why can the lower missing-data MAE not be generalized?**  
Only one deterministic missingness pattern was tested, and it happened to remove some harmful updates.

**10. Does this project prove that CACC is safer?**  
No. It reports simulated gap, braking, and disturbance indicators without field crash evidence or external validation.

**11. What evidence could support adoption later?**  
A design that improves target metrics without increasing hard braking, reduces safety overrides, keeps zero final-guard activations across paired seeds, and performs well on measured trajectories.

**12. What is the central engineering conclusion?**  
CACC feedforward improves some indicators relative to matched ACC but introduces tradeoffs, so the current design should be revised and retested.

## 19. Concept-to-file index

| Topic | File |
|---|---|
| Parameters and 12 scenarios | `configs/scenarios.json` |
| IDM, ACC/CACC, ramp control, and safety supervisor | `src/cavsim/core.py` |
| Detector audit, estimation, forecast, and missing test | `src/cavsim/observation.py` |
| Predictions and interpretations for every experiment | `outputs/results/experiment_record.csv` |
| Final quantitative results | `outputs/results/scenario_metrics.csv` |
| Evolution of the design | `deliverables/design_record.md` |
| Literature-to-equation/parameter trace | `deliverables/source_to_design_table.md` |
| Eight-minute script and defense | `deliverables/presentation_script.md` |
| Requirement completion audit | `deliverables/submission_checklist.md` |

