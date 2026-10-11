# Final presentation source - 8 minutes

## Slide 1 - CACC adds value over ACC, but the design is not adoption-ready

Question: At 50% and 100% penetration, does delayed predecessor-acceleration feedforward reduce a braking disturbance relative to matched ACC while maintaining throughput and bounded gaps?

Key result: at 50%, CACC lowers amplification 12.5% and raises minimum gap 11.4% versus ACC, with unchanged throughput, but increases delay 14.6%.

Decision: Revise before adoption.

## Slide 2 - One common environment; one isolated controller change

2.5-km one-lane freeway; deterministic mainline/ramp demand to 600 s; 300-s clearance; 12-vehicle initial platoon; on-ramp queue/storage; 300-m speed bottleneck; two virtual detectors. Same initialization, demand, disturbance, ramp logic, seed, and metrics in every matched comparison.

## Slide 3 - CACC = bounded ACC + one delayed feedforward term

Human: IDM. ACC: constant-time-headway PD spacing plus speed control. CACC: ACC plus `0.8 a_lead(t-delay)` from the immediate equipped predecessor. Commands are updated every 0.1 s, clipped to `[-4, 2] m/s2`, and passed through a 0.5-s first-order actuator. Missing/stale communication invokes ACC fallback. A final controller-level safety supervisor checks one-step clearance and stopping distance against a 2.0-m net-gap floor.

## Slide 4 - The decision trace proves what the controller knew

At 8.0 s, `veh_0003` has ego speed 24.754 m/s, gap 32.418 m, relative speed -1.100 m/s, and a 0.2-s-old predecessor acceleration message of -0.325 m/s2. The bounded CACC command is -0.392 m/s2. A nearby equipped vehicle behind a human predecessor receives no message and logs `ACC_fallback`.

## Slide 5 - Communication improves matched ACC, not every baseline metric

At 50%, ACC/CACC delay is 1.700/1.947 veh-h, amplification 0.722/0.631, minimum gap 4.670/5.203 m, and hard-braking counts 80/80. The final numerical collision guard has zero activations in every final scenario. Human amplification is already lower at 0.596, so the evidence supports only the narrower ACC-vs-CACC claim.

## Slide 6 - Benefits persist under demand, then erode under degraded messages

High-demand CACC-50 exits 377 vehicles versus human 347 and cuts delay 26.7%, but hard-braking events rise from 33 to 76. With 0.8-s delay and 30% dropout, CACC-50 delay rises 3.8%, amplification 5.5%, and hard-braking events 18.8%. Fallback and safety supervision remain bounded.

## Slide 7 - Checks passed; two negative results remain visible

Free-motion/equilibrium/conservation tests pass. All 12 final scenarios maintain at least 2.0 m and record zero final numerical-guard activations. Ten detector intervals have zero recount error. 0.05/0.10/0.20-s results are stable. Exponential smoothing beats the moving-average baseline, but one missingness pattern unexpectedly lowers its MAE. The ALINEA-like feedback loop works yet underperforms unmetered release in nominal demand.

## Slide 8 - Keep the architecture; reject the present tuning

Supported: predecessor acceleration has incremental value over matched ACC. Unsupported: crash reduction, external validation, beneficial missingness, or superior ramp metering. Next test: tune gain/headway subject to no increase in hard braking, fewer safety overrides, zero final-guard activations, paired demand/equipment seeds, and measured-trajectory validation.

