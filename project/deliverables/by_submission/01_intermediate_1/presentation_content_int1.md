# Intermediate 1 - Google Slides copy-ready content

Use the two-slide version for the presentation. If only one contribution slide is allowed, use Slide 1 and keep the cross-check paragraph from Slide 2 in the speaker notes.

---

## Slide 1 - Team Responsibilities and Integration

### Title

**Team Responsibilities and Integration**

### Subtitle

**Intermediate 1 · Human-driver baseline · Ramp meter control off**

### Left column

**Seunghun Oh**  
*Vehicle Dynamics & Numerical Verification*

- Implemented and verified the Intelligent Driver Model (IDM)
- Owned vehicle motion updates and trajectory outputs
- Checked free motion, equilibrium, conservation, and time-step sensitivity
- Main finding: the braking disturbance faded, with a speed-drop ratio of **0.66**
- Confirmed that the **0.1 s** simulation step was adequate

### Right column

**Ruopeng**  
*Boundaries, Merge & Observations*

- Implemented random arrivals, mainline entry, ramp storage, and merging
- Modeled the on-ramp merge as the bottleneck (speed cap, merge braking limit, zipper turns)
- Owned D1/D2 detector observations and the live visualization
- Main finding: the queue formed at the **merge (x = 1,600 m)**, spread about **1 km** back, and cleared after demand ended
- Identified a limitation: yielding vehicles stop completely, so the merge loses about 40% of its capacity

### Bottom integration line

**Integration:** Vehicle dynamics generated the trajectories; boundary and observation modules converted them into demand, queue, detector, and performance evidence.

### Suggested visual layout

Place a simple arrow between the two columns:

**Demand & road conditions → Vehicle dynamics → Trajectories → Detectors & evaluation**

### Speaker notes - Seunghun Oh

> I was responsible for the vehicle-dynamics side of the simulation. I worked with the IDM acceleration equation, vehicle-state updates, and trajectory outputs. I also checked the model under free-motion and equilibrium conditions and compared time steps of 0.05, 0.1, and 0.2 seconds. My main result was that the braking disturbance faded as it moved through the platoon: the maximum follower speed drop was 66 percent of the braking vehicle's speed drop. The sensitivity test also showed that a 0.1-second step was adequate for this experiment.

### Speaker notes - Ruopeng

> I was responsible for the roadway boundaries and observation side of the simulation. This included random vehicle arrivals, mainline entry, the ramp merge rule, virtual detectors D1 and D2, and the live visualization. My main result was that the merge itself is the bottleneck: without ramp traffic no queue forms, but with it a queue starts at the merge at 1,600 meters, spreads about one kilometer back with stop-and-go waves, and clears after arrivals stop. I also identified a limitation of our zipper rule: every yielding vehicle stops completely, so the merge passes about 40 percent less traffic than the lane capacity.

### Transition to the next slide

> We did not verify only our own modules. Each of us also checked one interface produced by the other person's component.

---

## Slide 2 - Cross-Verification and Evidence

### Title

**Cross-Verification and Evidence**

### Main table

| Presenter | Own evidence | Partner-interface check | What the check demonstrates |
|---|---|---|---|
| **Seunghun Oh** | `trajectories.csv`; minimum gap; overlap count; hardest braking; time-step comparison | Recounted D1/D2 crossings and compared them with `observations.csv` | Detector counts are traceable to individual vehicle crossings |
| **Ruopeng** | `observations.csv`; `control_commands.csv`; ramp queue; live view | Checked generated vehicles against exited vehicles, active vehicles, and boundary queues | Vehicle conservation holds across the complete simulation |

### Vehicle traces

**Seunghun's cross-module trace**

- `veh_0358`: arrived at the ramp at **472 s**
- Waited **10 s**; mainline vehicle `veh_0254` braked to leave a slot (zipper)
- Merged at **482 s**, then followed the IDM to the exit

**Ruopeng's cross-module trace**

- `veh_0010`: braking vehicle in the initial platoon
- Braked at **−2.5 m/s²** from **8–12 s**
- The eight following vehicles experienced smaller speed drops

### Bottom takeaway

**The model is reproducible and internally consistent:** detector counts match crossing records, vehicle conservation holds, overlap count is zero, and the minimum simulated gap is **1.8 m**.

### Speaker notes - Seunghun Oh

> To check Ruopeng's observation interface, I compared every detector count with the individual crossings recorded during the same 30-second interval. The totals matched, so the detector results can be traced back to vehicle-level events. I also followed ramp vehicle 0358 across the interface. It arrived at 472 seconds, waited 10 seconds in the ramp queue, entered at 482 seconds when mainline vehicle 0254 braked to leave a slot, and then continued under the same IDM dynamics as the mainline vehicles.

### Speaker notes - Ruopeng

> To check Seunghun's vehicle-state interface, I performed the conservation test. The number of generated vehicles must equal the vehicles that exited plus those still active or waiting in a boundary queue. This equality held in the final run. I also traced vehicle 0010 during the four-second braking event and used the follower trajectories to verify the 0.66 speed-drop ratio. Together, these checks connect the vehicle-level dynamics with the network-level observations.

### Closing transition

> These validated interfaces give us a reliable human-driver baseline for the CAV pathway, where we will compare ACC and CACC responses against the same disturbance and bottleneck.

---

## Optional one-slide compressed version

### Title

**Team Responsibilities and Verification**

### Seunghun Oh - Vehicle Dynamics

- IDM acceleration and vehicle-state updates
- Trajectory, minimum-gap, overlap, and braking metrics
- Time-step sensitivity: 0.05 / 0.1 / 0.2 s
- Finding: disturbance faded; speed-drop ratio = **0.66**
- Cross-check: detector observations matched crossing records

### Ruopeng - Network Boundaries & Observations

- Arrivals, ramp merge (the bottleneck), D1/D2, and live view
- Observation and control-command interfaces
- Finding: queue began at the **merge (1,600 m)**, spread about **1 km**, and later cleared
- Limitation: full stops at the zipper cost about 40% of merge capacity
- Cross-check: complete vehicle-conservation balance

### Takeaway

**Complementary ownership + cross-verification = a traceable baseline for the CAV experiments.**

### 60-second combined script

> Seunghun owned the vehicle-dynamics layer: the IDM equation, motion updates, trajectory output, and numerical checks. His main conclusion was that the braking disturbance faded, with a speed-drop ratio of 0.66, and that the 0.1-second time step was adequate. Ruopeng owned the network-boundary and observation layer: arrivals, the ramp merge, D1 and D2, and the live view. His main conclusion was that the merge itself is the bottleneck: the queue formed at the merge, spread about one kilometer back, and cleared after demand ended, while full stops at the zipper remained a limitation. We also cross-checked each other's interfaces: Seunghun verified detector counts against crossing records, and Ruopeng verified complete vehicle conservation. This gives us a traceable human-driver baseline for the later ACC and CACC comparison.

---

## Slide footnote / source line

**Source:** Intermediate 1 design record, experiment record, contribution record, and simulation outputs (`int1_results.json`, trajectories, crossings, observations, and queues).
