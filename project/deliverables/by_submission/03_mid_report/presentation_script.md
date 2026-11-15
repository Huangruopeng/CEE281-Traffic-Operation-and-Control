# Mini-presentation script (6-8 min) - mid-report scope

Deck: https://claude.ai/artifact/Y5WnGvAuMQDzxTKs1rzTb4 (the same text is in each slide's speaker notes).
Slides 1-11 are the talk (about 7 min: Seunghun about 3:15, Ruopeng about 2:55 plus a 1-min live demo);
slides 12-20 are backup for questions.

Live demo: `python run_live.py --port 8781`, open http://127.0.0.1:8781. Run 4, no meter, jump to 7 min (D1 congested
since 6:30, about 100 cars waiting); then ramp meter ALINEA 13% and jump again (no congestion, about 27 cars wait on the ramp).

| # | Slide | Who | Time |
|---|---|---|---|
| 1 | When does an on-ramp merge jam, and do automated vehicles help? | Ruopeng | 0:15 |
| 2 | One road, one bottleneck | Ruopeng | 0:30 |
| 3 | How vehicles drive: one model, a shorter gap for CAV pairs | Seunghun | 0:40 |
| 4 | Merge rule: two modes, split at 40 km/h | Seunghun | 0:45 |
| 5 | Congestion, measured at a detector | Ruopeng | 0:25 |
| 6 | Question and prediction | Seunghun | 0:35 |
| 7 | CAVs cut congestion from about half the vehicles on | Seunghun | 0:45 |
| 8 | Even 100% CAVs can break down after a burst of arrivals | Seunghun | 0:30 |
| 9 | Basic TMC: a ramp meter with ALINEA | Ruopeng | 0:30 |
| 10 | Metering helps above capacity, if the target is low enough | Ruopeng | 0:35 + 1:00 demo |
| 11 | Next tests, and who did what | Ruopeng | 0:40 |
| 12 | Human drivers: congested above capacity, sometimes below | backup | - |
| 13 | Backup: IDM parameters | backup | - |
| 14 | Backup: TMC settings | backup | - |
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

**3. How vehicles drive: one model, a shorter gap for CAV pairs (Seunghun)**
> Every driver follows the Intelligent Driver Model. The first term speeds the vehicle up toward its desired speed, 120 km/h; the second brakes it when the gap is smaller than the desired gap, which grows with speed through the time gap T. All values come from the textbook, Table 11.2, the same as Lecture 4. An automated vehicle, a CAV, uses the same model with one change: when the vehicle ahead is also a CAV, it gets that vehicle's data by vehicle-to-vehicle communication and follows at 0.6 seconds, the CACC gap from Lecture 7. Behind a human driver it keeps 1 second. So only CAV pairs gain.

**4. Merge rule: two modes, split at 40 km/h (Seunghun)**
> Our merge rule has two modes, split at 40 kilometers per hour. Above 40, on the left: a ramp car enters a gap only if the car behind it needs to brake less than 4 meters per second squared; at lower speeds this limit grows, up to 17 when stopped. Otherwise the ramp car waits. Below 40, on the right: cars in a queue are only about 7.5 meters apart, but a ramp car needs 9 meters, so it could never get in. So we use a zipper: the first mainline car within 100 meters stops, one ramp car goes in, then one mainline car, and so on. Two more numbers: a ramp car enters at most at 89 kilometers per hour, from the AASHTO design guide, and no car brakes harder than 9 meters per second squared, about the limit of a real car.

**5. Congestion, measured at a detector (Ruopeng)**
> We judge congestion the way a traffic center would, from detector D1, 150 meters before the merge. A 30-second interval is congested when its mean speed is below 11.1 meters per second, 40 kilometers per hour, and a run is congested when at least four intervals in a row are. On the right, without CAVs the speed drops to about 2 meters per second; with half CAVs it stays near 30.

**6. Question and prediction (Seunghun)**
> Our question: the demand is 2,600 vehicles per hour, 3 percent more than the lane can carry with human drivers. How many CAVs keep the merge from jamming, and if it still jams, are the waves weaker? The curve shows how much the lane can carry as the CAV share grows. It rises slowly at first, because only CAV pairs gain, and passes our demand at about 30 percent CAVs. So we predicted jams in nearly every run up to 30 percent, almost none from 80 percent, and waves as strong as before. We wrote this down before running.

**7. CAVs cut congestion from about half the vehicles on (Seunghun)**
> These are the means over 20 seeds. Panel a: with human time gap 1 second, congestion stays in most runs up to 40 percent CAVs, then drops: 30 percent of runs at half CAVs, and 5 percent at 100 percent. Panel b: the vehicles waiting at 10 minutes fall from about 100 to 8. So the timing matches the capacity curve. But two predictions failed. Congestion never disappears completely, and in panel c, when a queue does form with many CAVs, vehicles stop more often, 6 to 8 times instead of 4.

**8. Even 100% CAVs can break down after a burst of arrivals (Seunghun)**
> Here are single runs. Without CAVs a queue grows back from the merge; with half or all CAVs it disappears. But on the right, even with 100 percent CAVs, seed 284 breaks down. In that run 24 ramp vehicles arrive in one minute, twice the mean. Once the zipper starts, the merge passes about 1,500 vehicles per hour no matter how many CAVs there are, because the zipper vehicles stop completely.

**9. Basic TMC: a ramp meter with ALINEA (Ruopeng)**
> The other way to prevent a jam is a traffic management center, or TMC. Ours runs a ramp meter, a signal at the end of the ramp. Every 30 seconds it reads the occupancy at D2, after the merge. If D2 is busier than the target, ALINEA lets fewer ramp cars go; if not, more. The target, 17 percent, is the occupancy at capacity of our road; we also tried lower targets. If the detector data are lost, it falls back to a fixed rate. We compare it with no meter and with fixed rates.

**10. Metering helps above capacity, if the target is low enough (Ruopeng)**
> Without CAVs, metering helps: congestion drops from 95 percent of runs to 30, and the total delay from about 10 to 7 or 8 vehicle-hours, even counting the time vehicles wait on the ramp. But the target matters. At 17 percent, the occupancy at capacity, ALINEA hardly acts; a lower target, 13 percent, acts earlier. When we cut the detector data, the meter falls back to the fixed rate and still works. With half CAVs, all controllers give about the same delay.
>
> [Live demo, about 1 min: Run 4, no meter, jump to 7 min: D1 says congested since 6:30 and about 100 cars wait. Switch the meter to ALINEA 13% and jump again: no congestion; the cars wait on the ramp instead (about 27).]

**11. Next tests, and who did what (Ruopeng)**
> Three things we found and test next. First, zipper cars stop completely, so a jammed merge passes only about 1,500 vehicles per hour, even with all CAVs; we will let them slow down instead and let CAVs open a gap. Second, our CAVs do not use the acceleration of the car ahead, as real CACC does, which likely explains the extra stops; we will add it. Third, our results depend a lot on how often a waiting ramp driver checks the gap, so we will base it on reaction times. Seunghun built the vehicle model, the merge rule and the CAVs; I built the arrivals, the detectors, the TMC and the live view. Thank you.
