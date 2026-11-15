# Mini-presentation script (6-8 min) - mid-report scope

Deck: https://claude.ai/artifact/Y5WnGvAuMQDzxTKs1rzTb4 (the same text is in each slide's speaker notes).
Slides 1-14 are the talk (about 8 min: Seunghun about 4:05, Ruopeng about 4:00); slides 15-20 are backup for questions.

| # | Slide | Who | Time |
|---|---|---|---|
| 1 | When does an on-ramp merge jam, and do automated vehicles help? | Ruopeng | 0:15 |
| 2 | One road, one bottleneck | Ruopeng | 0:30 |
| 3 | Vehicle model: Intelligent Driver Model | Seunghun | 0:30 |
| 4 | Automated vehicles: same model, shorter gap behind a CAV | Seunghun | 0:30 |
| 5 | Merge rule: how a ramp vehicle gets in | Seunghun | 1:10 |
| 6 | Congestion, measured at a detector | Ruopeng | 0:25 |
| 7 | Question and prediction | Seunghun | 0:40 |
| 8 | Human drivers: congested above capacity, sometimes below | Ruopeng | 0:35 |
| 9 | CAVs cut congestion from about half the vehicles on | Seunghun | 0:45 |
| 10 | Even 100% CAVs can break down after a burst of arrivals | Seunghun | 0:30 |
| 11 | Basic TMC: a ramp meter with ALINEA | Ruopeng | 0:40 |
| 12 | Metering helps above capacity, if the target is low enough | Ruopeng | 0:40 |
| 13 | Problems found and next tests | Ruopeng | 0:40 |
| 14 | Who did what | Ruopeng | 0:15 |
| 15 | Checks before we trust the results | backup | - |
| 16 | Human drivers: predicted vs. observed | backup | - |
| 17 | Stop-and-go waves inside the queue | backup | - |
| 18 | Below capacity, the merge can still break down | backup | - |
| 19 | One TMC run, step by step | backup | - |
| 20 | What changed since Intermediate 1 | backup | - |

---

**1. When does an on-ramp merge jam, and do automated vehicles help? (Ruopeng)**
> Hi, we are Group 8, Seunghun and Ruopeng. Our project asks when an on-ramp merge turns into a traffic jam, and whether automated vehicles or a ramp meter can prevent it.

**2. One road, one bottleneck (Ruopeng)**
> This is our road: one lane, 2.5 kilometers. Mainline vehicles arrive at 1,900 vehicles per hour, ramp vehicles at 200 or 700, at random times. They arrive for ten minutes, and each run lasts fifteen so queues can clear. Ramp vehicles wait in a ramp queue of 35 places. Detector D1 sits just before the merge and D2 after it; both report every 30 seconds. Without ramp traffic there is never congestion, so the merge is the only bottleneck.

**3. Vehicle model: Intelligent Driver Model (Seunghun)**
> Every driver follows the Intelligent Driver Model. The first term accelerates the vehicle toward its desired speed; the second brakes it when the gap s is smaller than the desired gap s-star, which grows with speed through the time gap T. All values come from Treiber and Kesting, Table 11.2, the same as Lecture 4. We update positions and speeds every 0.1 seconds.

**4. Automated vehicles: same model, shorter gap behind a CAV (Seunghun)**
> An automated vehicle, or CAV, follows the same IDM with one change. When the vehicle ahead is also a CAV, it gets that vehicle's data by vehicle-to-vehicle communication and can follow at 0.6 seconds, the CACC gap from Lecture 7. Behind a human driver it keeps the human 1 second. So only CAV pairs gain, and with a CAV share p, a share p squared of vehicles drive closer. Keeping everything else equal isolates the effect of the time gap.

**5. Merge rule: how a ramp vehicle gets in (Seunghun)**
> Our merge rule has two modes, split at 40 kilometers per hour. Above 40, on the left: a ramp car enters a gap only if the car behind it needs to brake less than 4 meters per second squared. This limit grows as traffic slows, up to 17 when stopped, because braking hard at low speed isn’t very dangerous. If the gap fails, the ramp car waits. Below 40, on the right: cars in a queue are only about 7.5 meters apart, but a ramp car needs 9 meters, 5 for the car and 2 in front and behind. So it could never get in. So we use a zipper: the first mainline car within 100 meters stops before the merge point, one ramp car goes in, then one mainline car, and so on. Two more numbers. A ramp car enters at the speed of the car ahead, but at most 89 kilometers per hour, because the ramp is short. And no car brakes harder than 9 meters per second squared, about the limit of a real car. These rules come from the MOBIL model in our textbook and Lecture 4, and the AASHTO design guide.

**6. Congestion, measured at a detector (Ruopeng)**
> We judge congestion the way a traffic center would, from detector D1, 150 meters before the merge. A 30-second interval is congested when its mean speed is below 11.1 meters per second, 40 kilometers per hour, and a run is congested when at least four intervals in a row are. On the right, without CAVs the speed drops to about 2 meters per second; with half CAVs it stays near 30.

**7. Question and prediction (Seunghun)**
> Our question: at 2,600 vehicles per hour, which is 103 percent of the human capacity, how large a CAV share keeps the merge from congesting, and are the waves weaker when it still congests? The curve shows the capacity of mixed traffic from the IDM equilibrium. It rises slowly at first, because only CAV pairs gain, and passes our demand at about 32 percent CAVs. So we predicted congestion in nearly every run below that, some runs up to 60 percent, almost none above 80 percent, and waves as strong as before. We wrote this down before running.

**8. Human drivers: congested above capacity, sometimes below (Ruopeng)**
> First, human drivers only. Each panel shows every vehicle over time; red means slow. Over 20 seeds, the runs with demand above capacity, Runs 4 and 6, are congested almost every time, and the others not, except Run 2: at 88 percent of capacity it still breaks down in 15 percent of runs. Once it breaks down, the merge passes only about 1,500 vehicles per hour, because every zipper vehicle stops completely.

**9. CAVs cut congestion from about half the vehicles on (Seunghun)**
> These are the means over 20 seeds. Panel a: with human time gap 1 second, congestion stays in most runs up to 40 percent CAVs, then drops: 30 percent of runs at half CAVs, and 5 percent at 100 percent. Panel b: the vehicles waiting at 10 minutes fall from about 100 to 8. So the timing matches the capacity curve. But two predictions failed. Congestion never disappears completely, and in panel c, when a queue does form with many CAVs, vehicles stop more often, 6 to 8 times instead of 4.

**10. Even 100% CAVs can break down after a burst of arrivals (Seunghun)**
> Here are single runs. Without CAVs a queue grows back from the merge; with half or all CAVs it disappears. But on the right, even with 100 percent CAVs, seed 284 breaks down. In that run 24 ramp vehicles arrive in one minute, twice the mean. Once the zipper starts, the merge passes about 1,500 vehicles per hour no matter how many CAVs there are, because the zipper vehicles stop completely.

**11. Basic TMC: a ramp meter with ALINEA (Ruopeng)**
> The other way to prevent a jam is a traffic management center, or TMC. Ours runs a ramp meter, a signal at the end of the ramp. Every 30 seconds it reads the occupancy at D2, after the merge. If D2 is busier than the target, ALINEA lowers the release rate; if not, it raises it. The gain of 70 comes from the ALINEA paper, the rate bounds from FHWA, and the target of 17 percent is the occupancy at capacity of our road. If the ramp queue gets close to full, it opens up, and if the detector data are lost, it falls back to a fixed rate. We compare it with no meter and with fixed rates.

**12. Metering helps above capacity, if the target is low enough (Ruopeng)**
> Without CAVs, metering helps: congestion drops from 95 percent of runs to 30, and the total delay from about 10 to 7 or 8 vehicle-hours, even counting the time vehicles wait on the ramp. But the target matters. At 17 percent, the occupancy at capacity, ALINEA hardly acts; a lower target, 13 percent, acts earlier. When we cut the detector data, the meter falls back to the fixed rate and still works. With half CAVs, all controllers give about the same delay.

**13. Problems found and next tests (Ruopeng)**
> These are the problems we found and what we test next. First, zipper vehicles stop completely, which limits the merge to about 1,500 vehicles per hour; we will let them slow down instead and let CAVs open a gap. Second, our CAVs lack the acceleration feedforward of real CACC, which likely explains the extra stops. Third, we found that how often a waiting ramp driver checks the gap changes the result a lot, so we will base it on reaction times. Fourth, we picked the ALINEA target on the same runs, so we will tune it on separate seeds. Last, bursts of random arrivals; we will try a minimum headway.

**14. Who did what (Ruopeng)**
> Finally, our roles. Seunghun owns the vehicles, the merge rule and the CAVs; I own the boundaries, the detectors and the TMC. Each of us checks one output of the other's part. The code and every figure are in our repository, and we are happy to show a live run. Thank you.

**15. Checks before we trust the results (backup)**
> Every vehicle that enters is accounted for in all 820 runs. Unit tests check the IDM and the CAV time-gap rule. Detector counts match a recount of single crossings. Halving or doubling the time step changes the total delay by less than 4 percent and does not change the verdict. There were no collisions; the smallest gap was 1.5 meters. Without ramp traffic there is no congestion, so the merge is the cause.

**16. Human drivers: predicted vs. observed (backup)**
> With the seed we predicted for, all six predictions held. Over 20 seeds, Runs 4 and 6 are congested almost every time and Runs 1, 3 and 5 never, but Run 2 breaks down in 15 percent of runs although it is at 88 percent of capacity.

**17. Stop-and-go waves inside the queue (backup)**
> Inside the Run 4 queue, the dark red bands are stopped vehicles, and they move backward at about 15.5 kilometers per hour, close to the 15 observed on real freeways. One queued vehicle stops and restarts several times before it reaches the merge; on average about four times.

**18. Below capacity, the merge can still break down (backup)**
> Both panels are Run 2, 88 percent of capacity. With seed 281 nothing happens; with seed 284 a burst of arrivals breaks the merge down, and it stays congested for about eight and a half minutes, because the zipper passes only about 1,500 vehicles per hour. This matches Lecture 5B: a breakdown needs high demand, a bottleneck and a disturbance together.

**19. One TMC run, step by step (backup)**
> This is one TMC run with a 13 percent target. When the D2 occupancy goes above the target, the release rate drops, down to 240 vehicles per hour, and when it falls below, the rate rises again. The orange line is the same run with the D2 data cut at 5 minutes: the meter holds the 600 vehicle-per-hour fallback. The ramp queue stays below its 35 places in both.

**20. What changed since Intermediate 1 (backup)**
> First, what changed after your feedback on Intermediate 1. You told us not to use an artificial bottleneck, so we removed the slow zone. Now the only bottleneck is the on-ramp merge itself. You also asked us to randomize the vehicles, so arrival times are now random, following a Poisson process with the same average rates. Finally, the assignment asked for one focused question, so we combined our two earlier questions into one.
