# Eight-minute individual presentation script and defense notes

## Timing

- 0:00-0:40 - State the bounded question and prediction.
- 0:40-1:35 - Explain the common freeway and fair comparison.
- 1:35-2:40 - Show the IDM, ACC, and CACC control laws and exact inputs.
- 2:40-3:30 - Walk through one decision trace and fallback.
- 3:30-4:45 - Present nominal ACC/CACC ablation and human baseline.
- 4:45-5:45 - Present penetration, delay/dropout, demand, and stronger-braking tests.
- 5:45-6:35 - Present verification, detector/forecast, and time-step evidence.
- 6:35-7:20 - Identify the failure condition and limitations.
- 7:20-8:00 - Defend “revise before adoption” and name the next falsifying test.

## Decision-trace explanation

At each 0.1-s control update, an equipped vehicle measures ego speed, gap, and relative speed. ACC forms a speed command and a constant-time-headway gap command; the smaller command is bounded to `[-4, 2] m/s2`. CACC adds `0.8` times the delayed acceleration message from its immediate equipped predecessor. If the predecessor is human, a packet drops, or no sufficiently old message exists, feedforward is zero and the mode is logged as `ACC_fallback`. A controller-level safety supervisor then checks one-step clearance and differential stopping distance against a 2.0-m physical net-gap floor; an active limit is logged as `safety_override`. A first-order 0.5-s actuator response converts ordinary commands to motion, while a safety override applies the necessary bounded braking immediately.

## Likely questions

**Why is the human baseline amplification lower than CACC?** The chosen IDM parameters and initial spacing already dissipate this pulse. The project therefore does not claim CACC beats human driving on that metric; it claims a narrower 12.5% improvement over matched ACC.

**Does the 5.203-m CACC minimum gap prove safety?** No. The model maintains at least the declared 2.0-m physical clearance and records zero final numerical-guard activations across all 12 scenarios, but this is simulation verification, not crash-risk validation. The remaining hard-braking frequency and dependence on the safety supervisor still argue against deployment claims.

**What does the controller know?** Only current local kinematics and a delayed predecessor acceleration message. The disturbance schedule, future trajectories, and evaluation truth are excluded.

**Why did missing data improve forecast MAE?** The removed intervals happened to contain updates that hurt the one-step smoother. With one deterministic series, this is a pattern-specific counterexample, not evidence that missingness is beneficial.

**Why did ALINEA-like feedback not improve delay?** Nominal demand clears and the occupancy measure is a 50-m simulation proxy. The selected target/gain holds more ramp traffic without relieving a binding enough mainline constraint. It needs calibration under heavier conditions.

**Which result would change your conclusion?** If a gain/headway design can reduce delay and ACC amplification without exceeding the human hard-braking count, while remaining stable across arrival/equipment seeds and measured-trajectory validation, the adoption decision could become favorable.

