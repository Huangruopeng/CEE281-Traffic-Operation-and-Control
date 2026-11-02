# Intermediate 2 progress presentation — script (about 10 min)

The same English text is in the speaker notes of each slide. Split: Seunghun about 5 min (slides 1, 4, 5, 7, 10, 12),
Ruopeng about 5 min (slides 2, 3, 6, 8, 9, 11, 13). Change the split freely.

| # | Slide | Who | Time |
|---|---|---|---|
| 1 | Title | Seunghun | 0:20 |
| 2 | What changed since Intermediate 1 | Ruopeng | 0:40 |
| 3 | One road, one bottleneck | Ruopeng | 0:50 |
| 4 | Vehicle model: IDM | Seunghun | 1:00 |
| 5 | Merge rule | Seunghun | 1:10 |
| 6 | Checks | Ruopeng | 0:50 |
| 7 | Question and prediction | Seunghun | 0:50 |
| 8 | Results: six runs | Ruopeng | 0:40 |
| 9 | Predicted vs. observed | Ruopeng | 0:40 |
| 10 | Stop-and-go waves | Seunghun | 0:50 |
| 11 | Breakdown below capacity | Ruopeng | 1:00 |
| 12 | Problems and next tests | Seunghun | 1:00 |
| 13 | Who did what | Ruopeng | 0:20 |

---

**1. Title (Seunghun)**
> Hi, we are Seunghun and Ruopeng. Our project asks a simple question: when does an on-ramp merge turn into a traffic jam? Today we’ll show our simulation, the merge rule we use, our prediction, and the results of six runs.

*(램프 합류가 언제 정체가 되는지 묻는 프로젝트. 시뮬레이션, 합류 규칙, 예측, 6개 실험 결과를 보여줄 것.)*

**2. What changed since Intermediate 1 (Ruopeng)**
> First, what changed after your feedback on Intermediate 1. You told us not to use an artificial bottleneck, so we removed the slow zone. Now the only bottleneck is the on-ramp merge itself. You also asked us to randomize the vehicles, so arrival times are now random, following a Poisson process with the same average rates. Finally, the assignment asked for one focused question, so we combined our two earlier questions into one.

*(피드백 반영: 인공 병목 제거 → 합류가 유일한 병목, 도착 무작위화(Poisson), 질문 하나로 합침.)*

**3. One road, one bottleneck (Ruopeng)**
> This is our road: one lane, 2.5 kilometers. Mainline vehicles enter on the left at 1,900 vehicles per hour. Ramp vehicles join at 1.6 kilometers, at 200 or 700 vehicles per hour. Vehicles arrive for ten minutes, and we run for fifteen so that queues can clear. Ramp vehicles wait in a ramp queue that holds 35 vehicles; the ramp meter exists in the code but is off in all runs. Detectors D1 and D2, before and after the merge, report counts and speeds every 30 seconds. To check that the merge really is the cause, we ran the same case without ramp traffic, and no queue formed.

*(1차로 2.5 km, 본선 1,900대, 램프 200/700대, 10분 도착·15분 실행, 램프 대기 35대, 신호 꺼짐, 검지기 30초. 램프 차가 없으면 정체도 없음 → 합류가 원인.)*

**4. Vehicle model: IDM (Seunghun)**
> Every driver follows the Intelligent Driver Model. The first part accelerates the vehicle toward its desired speed; the second part brakes when the gap s is smaller than the desired gap s-star. The desired gap grows with speed through vT, and with the closing speed through the last term. All parameters come from Treiber and Kesting, Table 11.2, which are the same values as in Lecture 4, page 37. The time gap T is the parameter we vary in our experiment. In the code this is the function idm_acceleration in core.py, and the values are in scenarios.json. We update positions and speeds every 0.1 seconds. The main assumptions are identical drivers, no reaction time, and one lane.

*(IDM 식 설명: 첫 항은 원하는 속도로 가속, 둘째 항은 간격이 원하는 간격보다 작으면 감속. 값은 교재 표 11.2 = 강의 04 p37. T가 실험 변수. 코드 위치, 0.1초 갱신, 가정.)*

**5. Merge rule (Seunghun)**
> Our merge rule has two modes, split at 40 kilometers per hour.
>
> Above 40, on the left: a ramp car enters a gap only if the car behind it needs to brake less than 4 meters per second squared. This limit grows as traffic slows, up to 17 when stopped, because braking hard at low speed isn’t very dangerous. If the gap fails, the ramp car waits.
>
> Below 40, on the right: cars in a queue are only about 7.5 meters apart, but a ramp car needs 9 meters, 5 for the car and 2 in front and behind. So it could never get in. So we use a zipper: the first mainline car within 100 meters stops before the merge point, one ramp car goes in, then one mainline car, and so on.
>
> Two more numbers. A ramp car enters at the speed of the car ahead, but at most 89 kilometers per hour, because the ramp is short. And no car brakes harder than 9 meters per second squared, about the limit of a real car.
>
> These rules come from the MOBIL model in our textbook and Lecture 4, and the AASHTO design guide.

*(두 모드, 기준 40 km/h. 40 이상: 뒤차가 4 m/s² 미만으로 감속하면 되는 틈일 때만 진입(멈춰 있으면 17까지 허용), 아니면 대기. 40 미만: 정체 간격 7.5 m < 필요 9 m(5 + 2 + 2)라 못 들어감 → 지퍼(100 m 안 첫 본선 차가 멈추고 한 대씩 번갈아). 진입 속도는 앞차 속도, 최대 89 km/h. 최대 제동 9 m/s². 출처는 마지막에 한 번.)*

**6. Checks (Ruopeng)**
> Before trusting the results we ran these checks. Every vehicle that enters is accounted for, whether it has exited, is still on the road, or is waiting, in all 30 runs. Unit tests check free motion on an empty road and the equilibrium gap in steady traffic. The detector counts match an independent recount of individual vehicle crossings. Halving or doubling the time step changes the total delay by less than four percent. We count collisions instead of preventing them, and there were none; the smallest gap was 1.65 meters. And when we remove ramp traffic, there is no queue, so the merge is the cause.

*(검증: 차량 수 보존, 단위 테스트, 검지기 재집계 일치, 시간 간격 바꿔도 4% 미만 차이, 충돌 0, 램프 없으면 정체 없음.)*

**7. Question and prediction (Seunghun)**
> Our question: under what desired time gap and ramp demand does the merge create a persistent queue with stop-and-go waves? Persistent means vehicles before the merge stay below 40 kilometers per hour for more than two minutes. The theory gives a simple rule: a queue persists only if demand is above capacity. The capacity comes from the IDM equilibrium, shown by these curves. A shorter time gap gives a higher capacity: about 2,970, 2,520 and 2,190 vehicles per hour. The dashed lines are our two demand levels. We turn two knobs, the time gap and the ramp demand, which gives six runs. We wrote these predictions on October 18, before running anything.

*(질문과 예측: 수요 > 용량일 때만 정체. 용량은 IDM 평형식에서 T별로 2,970/2,520/2,190. 손잡이 두 개 → 6개 실험. 10/18 실행 전에 예측 기록.)*

**8. Results: six runs (Ruopeng)**
> Here are the six runs. Each panel shows every vehicle over time, colored by speed; red means slow. The top row has 200 ramp vehicles per hour, the bottom row 700, and the time gap grows from left to right. Only Runs 4 and 6 show a queue, which are exactly the two runs where demand is above capacity. In both, the queue starts at the merge and grows backward. In Run 5, at 96 percent of capacity, we see only short slowdowns.

*(그림 읽는 법: 점 = 차, 빨강 = 느림. 정체는 수요가 용량을 넘은 4, 6번에서만. 5번(96%)은 잠깐 느려짐만.)*

**9. Predicted vs. observed (Ruopeng)**
> With the seed we predicted for, all six predictions held. We then repeated each run with four more random seeds. Runs 4 and 6 queued every time, and Runs 1, 3 and 5 never did. But Run 2, at only 88 percent of capacity, broke down in one of five seeds. The queues were also much larger than our lower bounds: 99 instead of at least 14, and 170 instead of at least 68. We will explain both of these in two slides.

*(예측한 시드에서 6개 모두 맞음. 시드 5개로 반복하니 2번(88%)이 5개 중 1개에서 정체. 정체 크기는 최소치보다 훨씬 큼. 이유는 두 장 뒤에서.)*

**10. Stop-and-go waves (Seunghun)**
> Here is the inside of the Run 4 queue. The red bands are stopped vehicles, and they move backward as time goes on. These are stop-and-go waves. We measured them moving backward at 15.5 kilometers per hour, and 16 in Run 6. Lecture 4 and the textbook give about 15 kilometers per hour, so the model reproduces this pattern. On the right is one vehicle in the queue: it stops and restarts about seven times before it reaches the merge. On average a queued vehicle stopped 3.6 times. If you like, we can also show this live in our visualization.

*(빨간 띠 = 멈춘 차들, 시간이 지나며 뒤로 이동 = 파동. 시속 15.5/16 km, 문헌 약 15 km와 일치. 차 한 대가 7번쯤 멈췄다 출발. 원하면 실시간 화면으로 보여줄 수 있음.)*

**11. Breakdown below capacity (Ruopeng)**
> This is the most interesting result. Both panels are Run 2: the same time gap and the same demand, 88 percent of capacity. With seed 281 nothing happens. With seed 284, random arrivals bunch up, the merge breaks down, and the queue lasts almost nine minutes. Once it breaks down, the merge passes only about 1,500 vehicles per hour, because each zipper vehicle stops completely. That is far below capacity, so the queue keeps growing. The same effect explains why our queues were much larger than the lower bounds. So demand above capacity is enough for a queue, but not the only way to get one: below capacity, a breakdown is possible but not certain. This matches Lecture 5B, which says a breakdown needs high demand, a bottleneck and a disturbance together.

*(같은 조건(88%)인데 무작위 도착에 따라 한 번은 정체. 한 번 깨지면 지퍼 차가 완전히 서서 시간당 약 1,500대만 통과 → 계속 쌓임. 그래서 "수요 > 용량"은 충분조건이지 유일한 경로가 아님. 강의 05B와 일치.)*

**12. Problems and next tests (Seunghun)**
> These are the problems we found and what we will test next. First, the zipper vehicle stops completely, which costs about 40 percent of capacity during a jam; next we will let it slow down instead of stopping. Second, in Run 6 the queue reached the road entrance and did not clear by 15 minutes, so we need a longer road or a longer run. Third, at a time gap of 1.2 seconds, random arrivals bunch up at the entrance; Lecture 3 warns that Poisson arrivals are less realistic near capacity, so we will try arrivals with a minimum headway. Fourth, we will use more seeds and report means with confidence intervals. Our next question is simple: if some cars are automated, does the merge jam less? We expect yes, because automated cars can follow closer, and that raises capacity. We will also check that the stop-and-go waves do not get worse.

*(찾은 문제 4개와 다음 시험: 지퍼 완전 정지 → 감속으로, 6번 정체가 입구까지 → 도로/시간 늘리기, 입구 뭉침 → 최소 간격 도착, 시드 1개 → 시드 늘리고 신뢰구간. 다음 질문: CAV를 섞으면 합류 정체가 줄까? 바짝 붙어 가서 용량이 커질 것으로 기대, 파동이 더 나빠지지 않는지도 확인.)*

**13. Who did what (Ruopeng)**
> Finally, our roles. Seunghun owns the vehicle model and the merge rule; I own the arrivals, the ramp queue and the detectors. Each of us checks one output of the other’s part. We’re happy to show the code or a live run. Thank you.

*(역할 분담. 코드나 실시간 실행을 보여줄 수 있음.)*

---

## Likely questions and short answers

- **Why 40 km/h for "persistent"?** Our own threshold for a clear queue; the speed at capacity is about 72 km/h, so 40 km/h only counts clear jams.
- **Why does the zipper vehicle stop completely?** Simplest rule that works; the course calls zipper merging hard to model (Lecture 04 p. 45). Testing a slow-down version is our next step.
- **Why no reaction time?** The textbook values are for the plain IDM; adding a reaction time is a planned sensitivity test, important later when we compare humans with ACC.
- **Where is the position updated?** `FreewaySimulation._advance()` in `src/cavsim/core.py`; ballistic update every 0.1 s.
- **How do you know the queue is not a coding artifact?** No queue without ramp traffic; conservation holds; detector recount matches; same result at 0.05 and 0.2 s.
