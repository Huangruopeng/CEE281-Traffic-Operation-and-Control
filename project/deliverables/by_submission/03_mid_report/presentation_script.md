# Mini-presentation script (6-8 min) - mid-report scope

Deck: https://claude.ai/artifact/Y5WnGvAuMQDzxTKs1rzTb4 (the same text is in each slide's speaker notes).
The slides follow the mid-report: 1 introduction (slides 2-3), 2 model (4-7), 3 results (8-11), 4-5 open problems
and next tests (12). Slides 1-12 are the talk (about 7 min: Seunghun about 3:20, Ruopeng about
2:45 plus a 1-min live demo); slides 13-21 are backup for questions.

Live demo: `python run_live.py --port 8781`, open http://127.0.0.1:8781. Run 4, no meter, jump to 7 min (D1 congested
since 6:30, about 100 cars waiting); then ramp meter ALINEA 13% and jump again (no congestion, about 27 cars wait on the ramp).

| # | Slide | Who | Time |
|---|---|---|---|
| 1 | When does an on-ramp merge jam, and do automated vehicles help? | Ruopeng | 0:15 |
| 2 | One road, one bottleneck | Ruopeng | 0:25 |
| 3 | Question and congestion rule | Ruopeng | 0:30 |
| 4 | How vehicles drive: one model, a shorter gap for CAV pairs | Seunghun | 0:35 |
| 5 | With CAVs the lane carries more, slowly at first | Seunghun | 0:25 |
| 6 | Merge rule: two modes, split at 40 km/h | Seunghun | 0:40 |
| 7 | Basic TMC: a ramp meter with ALINEA | Ruopeng | 0:30 |
| 8 | Human drivers: congested above capacity, sometimes below | Ruopeng | 0:35 |
| 9 | CAVs cut congestion from about half the vehicles on | Seunghun | 0:40 |
| 10 | Even 100% CAVs can break down after a burst of arrivals | Seunghun | 0:25 |
| 11 | Metering helps above capacity, if the target is low enough | Ruopeng | 0:30 + 1:00 demo |
| 12 | Open problems, next tests, and who did what | Seunghun | 0:35 |
| 13 | Backup: the congestion rule at D1 | backup | - |
| 14 | Backup: IDM parameters | backup | - |
| 15 | Backup: TMC settings | backup | - |
| 16 | Checks before we trust the results | backup | - |
| 17 | Human drivers: predicted vs. observed | backup | - |
| 18 | Stop-and-go waves inside the queue | backup | - |
| 19 | Below capacity, the merge can still break down | backup | - |
| 20 | One TMC run, step by step | backup | - |
| 21 | What changed since Intermediate 1 | backup | - |

---

**1. When does an on-ramp merge jam, and do automated vehicles help? (Ruopeng)**
> Hi, we are Group 8, Seunghun and Ruopeng. Our project asks when an on-ramp merge turns into a traffic jam, and whether automated vehicles or a ramp meter can prevent it.

**2. One road, one bottleneck (Ruopeng)**
> This is our road: one lane, 2.5 kilometers. Mainline vehicles arrive at 1,900 vehicles per hour, ramp vehicles at 200 or 700, at random times. They arrive for ten minutes, and each run lasts fifteen so queues can clear. Ramp vehicles wait in a ramp queue of 35 places. Detector D1 sits just before the merge and D2 after it; both report every 30 seconds. Without ramp traffic there is never congestion, so the merge is the only bottleneck.

**3. Question and congestion rule (Ruopeng)**
> Our question: the demand is 2,600 vehicles per hour, 3 percent more than the lane can carry with human drivers. What share of CAVs is needed so that the merge no longer becomes congested? And when it still does, does a queued vehicle stop fewer times? We call a 30-second interval at D1 congested when its mean speed is below 40 kilometers per hour, and a run congested when this lasts four intervals in a row, two minutes. Arrivals are random, so we run every CAV share with 20 seeds and report how many runs are congested.

**4. How vehicles drive: one model, a shorter gap for CAV pairs (Seunghun)**
> Every driver follows the Intelligent Driver Model. The first term speeds the vehicle up toward its desired speed, 120 km/h; the second brakes it when the gap is smaller than the desired gap, which grows with speed through the time gap T. All values come from the textbook, Table 11.2, the same as Lecture 4. An automated vehicle, a CAV, uses the same model with one change: when the vehicle ahead is also a CAV, it gets that vehicle's data by vehicle-to-vehicle communication and follows at 0.6 seconds, the CACC gap from Lecture 7. Behind a human driver it keeps 1 second. So only CAV pairs gain.

**5. With CAVs the lane carries more, slowly at first (Seunghun)**
> From the steady state of the IDM we get the capacity: 2,519 vehicles per hour with human drivers. With CAVs it rises, but slowly at first, because only CAV pairs drive closer, a share p squared. The lane can carry our demand from about 30 percent CAVs in Run 4, or 60 percent in Run 6, where the human drivers keep 1.2 seconds. We add CAVs to both runs.

**6. Merge rule: two modes, split at 40 km/h (Seunghun)**
> Our merge rule has two modes, split at 40 kilometers per hour. Above 40, on the left: a ramp car enters a gap only if the car behind it needs to brake less than 4 meters per second squared; at lower speeds this limit grows, up to 17 when stopped. Otherwise the ramp car waits. Below 40, on the right: cars in a queue are only about 7.5 meters apart, but a ramp car needs 9 meters, so it could never get in. So we use a zipper: the first mainline car within 100 meters stops, one ramp car goes in, then one mainline car, and so on. Two more numbers: a ramp car enters at most at 89 kilometers per hour, from the AASHTO design guide, and no car brakes harder than 9 meters per second squared, about the limit of a real car.

**7. Basic TMC: a ramp meter with ALINEA (Ruopeng)**
> The other way to prevent a jam is a traffic management center, or TMC. Ours runs a ramp meter, a signal at the end of the ramp. Every 30 seconds it reads the occupancy at D2, after the merge. If D2 is busier than the target, ALINEA lets fewer ramp cars go; if not, more. The target, 17 percent, is the occupancy at capacity of our road; we also tried lower targets. If the detector data are lost, it falls back to a fixed rate. We compare it with no meter and with fixed rates.

**8. Human drivers: congested above capacity, sometimes below (Ruopeng)**
> Before adding CAVs, we checked how the merge behaves with human drivers alone: does it become congested only when demand exceeds capacity? We ran six cases: three time gaps, each with a low and a high ramp demand. Each panel shows every vehicle over time; red means slow. Runs 4 and 6, above capacity, are congested almost every time. Run 2 is below capacity, at 88 percent, but still becomes congested in 15 percent of runs. Once congested, the merge passes only about 1,500 vehicles per hour, because every zipper vehicle stops completely. So at the demand of our question, Run 4, human drivers congest the merge in 95 percent of runs. That is our starting point: how many CAVs does it take to prevent this?

**9. CAVs cut congestion from about half the vehicles on (Seunghun)**
> We start from 95 percent congested runs without CAVs. Before running, we predicted congestion in nearly every run up to 30 percent CAVs, almost none from 80 percent, and as many stops as before. Panel a: congestion stays in most runs up to 40 percent CAVs, then drops: 30 percent of runs at half CAVs, 5 percent at all CAVs. Panel b: the vehicles still waiting at 10 minutes fall from about 100 to 8. So the timing matched. But congestion never disappears completely, and in panel c, when a queue does form with many CAVs, vehicles stop more often, 6 to 8 times instead of 4.

**10. Even 100% CAVs can break down after a burst of arrivals (Seunghun)**
> Here are single runs. Without CAVs a queue grows back from the merge; with half or all CAVs it disappears. But on the right, even with 100 percent CAVs, seed 284 breaks down. In that run 24 ramp vehicles arrive in one minute, twice the mean. Once the zipper starts, the merge passes about 1,500 vehicles per hour no matter how many CAVs there are, because the zipper vehicles stop completely.

**11. Metering helps above capacity, if the target is low enough (Ruopeng)**
> Without CAVs, metering helps: congestion drops from 95 percent of runs to 30, and the total delay from about 10 to 7 or 8 vehicle-hours, even counting the time vehicles wait on the ramp. But the target matters. At 17 percent, the occupancy at capacity, ALINEA hardly acts; a lower target, 13 percent, acts earlier. When we cut the detector data, the meter falls back to the fixed rate and still works. With half CAVs, all controllers give about the same delay.
>
> [Live demo, about 1 min: Run 4, no meter, jump to 7 min: D1 says congested since 6:30 and about 100 cars wait. Switch the meter to ALINEA 13% and jump again: no congestion; the cars wait on the ramp instead (about 27).]

**12. Open problems, next tests, and who did what (Seunghun)**
> Three open problems and our next tests. First, zipper cars stop completely, so a congested merge passes only about 1,500 vehicles per hour, even with all CAVs; we will let them slow down instead and let CAVs open a gap. Second, our CAVs do not use the acceleration of the car ahead, as real CACC does, which likely explains the extra stops. Third, our results depend a lot on how often a waiting ramp driver checks the gap, so we will base it on reaction times. I built the vehicle model, the merge rule and the CAVs; Ruopeng built the arrivals, the detectors, the TMC and the live view. Thank you.
