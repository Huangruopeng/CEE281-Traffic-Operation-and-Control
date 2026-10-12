# Intermediate 1 - overview script (about 2-3 min, final model)

Spoken before the team-responsibility slides in `presentation_content_int1.md`.
Numbers: `outputs/int1/int1_results.json` and `experiment_record.md` (Run 8).

## Script

**1. Question**
> Our question has two parts. First, when one car brakes suddenly, does the slowdown fade or grow as it
> passes back through the cars behind? Second, when cars from an on-ramp merge into a busy freeway, how far
> back does the slowdown spread, and does it clear?

**2. Road**
> We simulate a 2.5-kilometer, one-lane freeway with one on-ramp at 1.6 kilometers. There is no artificial
> bottleneck: the merge itself is the bottleneck. The mainline traffic alone uses about three quarters of
> the lane's capacity, but mainline plus ramp traffic is slightly more than the lane can carry. Cars arrive
> at random times for 10 minutes, and then arrivals stop.

**3. Model**
> Every car follows the Intelligent Driver Model with textbook values. For the merge we use three rules: a
> ramp car enters at no more than 89 kilometers per hour; it may enter only if the car behind it does not
> have to brake too hard; and in slow traffic, mainline cars take turns with ramp cars, like a zipper.

**4. Predictions**
> Before running, we predicted two things. First, the braking slowdown fades. Second, without ramp traffic
> there is no queue; with ramp traffic, a queue forms right before the merge, spreads back about half a
> kilometer, and clears after arrivals stop.

**5. Results**
> The slowdown faded: the cars behind lost at most 66 percent of the braking car's speed drop. Without ramp
> traffic there was no queue, so the merge is the cause. With ramp traffic, the queue started at the merge
> after about 5 minutes and spread back about 1 kilometer, twice what we predicted. Inside the queue, cars
> stopped and restarted three to four times each: stop-and-go waves. Everything cleared by about 13 minutes.

**6. Limitation and next step**
> The queue was longer than predicted because in our zipper rule the car that lets a ramp car in stops
> completely, so during the jam the merge passes about 40 percent less traffic than the lane can carry.
> Real drivers adjust earlier, so next we will let that car slow down instead of stopping. Then we will
> test automated vehicles on this same road.

**7. Hand-off**
> Now we will show how we split the work and checked each other's parts.

## Numbers to remember

- Road 2.5 km, merge at 1.6 km.
- Demand 1,900 (mainline) + 700 (ramp) cars per hour; lane capacity about 2,500 (75% and 103%).
- Speed-drop ratio 0.66.
- Queue: starts at 5.2 min, about 1 km long (103 cars), cleared at 12.9 min; ramp queue at most 7 cars.
- During the jam the merge passes about 1,500 cars per hour (40% below capacity).

## Likely questions

**How does the zipper rule work?**
> When traffic before the merge is slower than 40 km/h and a ramp car is waiting, the first mainline car
> within 100 meters of the merge acts as if a stopped car stood at the merge point, so it stops and leaves
> one car-length slot. The ramp car enters, and the next turn belongs to the mainline. A car too close to
> stop safely drives on, and the next car yields.

**Which parameter would you change, and what would happen?**
> The time gap T. With T raised from 1.0 to 1.6 seconds, the lane capacity drops from about 2,500 to about
> 1,740 cars per hour, below even the mainline traffic alone, so a queue would form even without ramp cars.
> We also tried a stronger brake, -3.5 instead of -2.5 m/s²: the ratio rose from 0.66 to 0.73, but the
> slowdown still faded.

**Are the stop-and-go waves real or caused by your rule?**
> Both. Each zipper turn makes one mainline car stop at the merge, and the queue moves at about 12 km/h,
> a speed at which the model's slowdowns grow instead of fading, so these stops travel back through the queue.

**Why random arrivals?**
> Real cars do not arrive evenly. We keep the same average rates and use one random seed; more seeds come later.
