#!/usr/bin/env python3
"""Dependency-free local server for the live view of the freeway merge simulation."""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time
import webbrowser

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = Path(__file__).resolve().parent / "web"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cavsim.core import FreewaySimulation


RUNS = {1: (0.8, 200.0), 2: (0.8, 700.0), 3: (1.0, 200.0), 4: (1.0, 700.0), 5: (1.2, 200.0), 6: (1.2, 700.0)}
METERS = {  # id: (label, mode, fixed rate [veh/h], ALINEA target occupancy [%], D2 lost from [s]) as in run_tmc.py
    "none": ("No meter", "unmetered", 600.0, 17.0, None),
    "fixed600": ("Fixed 600 veh/h", "fixed", 600.0, 17.0, None),
    "fixed900": ("Fixed 900 veh/h", "fixed", 900.0, 17.0, None),
    "alinea17": ("ALINEA, target 17%", "alinea", 600.0, 17.0, None),
    "alinea15": ("ALINEA, target 15%", "alinea", 600.0, 15.0, None),
    "alinea13": ("ALINEA, target 13%", "alinea", 600.0, 13.0, None),
    "alinea13_lost": ("ALINEA 13%, D2 lost at 5 min", "alinea", 600.0, 13.0, 300.0),
}
CAV_SHARES = [round(0.1 * k, 1) for k in range(11)]
SEEDS = list(range(281, 301))
SLOW_KMH = 40.0
SAMPLE_S = 2.0


def options() -> dict:
    return {"runs": [{"id": n, "T": T, "ramp": ramp} for n, (T, ramp) in RUNS.items()],
            "meters": [{"id": k, "label": v[0]} for k, v in METERS.items()],
            "cav_shares": CAV_SHARES, "seeds": SEEDS}


def build_case(config: dict, case: dict) -> tuple[FreewaySimulation, dict]:
    """A simulation for one choice of run (time gap x ramp demand), CAV share, ramp meter and seed."""
    from cavsim.metrics import capacity_vph

    T, ramp = RUNS[int(case["run"])]
    p = float(case["penetration"])
    label, mode, rate, target, lost_s = METERS[case["meter"]]
    s = dict(config["simulation"], seed=int(case["seed"]))
    meter_cfg = dict(config["ramp_meter"], fixed_rate_vph=rate, target_occupancy_pct=target)
    scenario = dict(config["base_scenario"], scenario_id=f"run{case['run']}_p{p}_{case['meter']}_s{case['seed']}",
                    ramp_demand_vph=ramp, penetration=p, meter_mode=mode)
    if lost_s is not None:
        scenario["detector_failure_from_s"] = lost_s
    cap = capacity_vph(dict(config["human_idm"], desired_time_gap_s=T), s["vehicle_length_m"], s["free_speed_mps"], p,
                       config["cav"]["desired_time_gap_s"])
    demand = scenario["mainline_demand_vph"] + ramp
    info = {"run": int(case["run"]), "T": T, "mainline_vph": scenario["mainline_demand_vph"], "ramp_vph": ramp,
            "penetration": p, "capacity_vph": round(cap), "demand_pct": round(100 * demand / cap), "seed": int(case["seed"]),
            "meter": case["meter"], "meter_label": label, "meter_mode": mode, "target_pct": target,
            "fixed_rate_vph": rate, "d2_lost_from_s": lost_s}
    sim = FreewaySimulation(s, dict(config["human_idm"], desired_time_gap_s=T), config["cav"], meter_cfg, scenario)
    return sim, info


class SimulationSession:
    def __init__(self, config: dict):
        self.config = config
        self.case = {"run": 4, "penetration": 0.0, "meter": "none", "seed": 281}  # Run 4 = the demand of our question
        self.speed = 1.0
        self.lock = threading.RLock()
        self.reset()

    def reset(self, case: dict | None = None) -> None:
        if case:
            new = dict(self.case, **{k: case[k] for k in ("run", "penetration", "meter", "seed") if k in case})
            if int(new["run"]) not in RUNS or new["meter"] not in METERS or int(new["seed"]) not in SEEDS \
                    or not 0.0 <= float(new["penetration"]) <= 1.0:
                raise ValueError(f"Unknown case: {case}")
            self.case = new
        self.sim, self.info = build_case(self.config, self.case)
        self.samples: list[dict] = []
        self.next_sample_s = 0.0
        self.playing = False
        self.last_wall_s = time.monotonic()
        self.sim_time_credit_s = 0.0

    def _step(self) -> None:
        self.sim.step()
        if self.sim.time_s + 1e-9 >= self.next_sample_s:
            self.next_sample_s += SAMPLE_S
            x_merge = float(self.sim.cfg["ramp_position_m"])
            slow = sum(1 for v in self.sim.vehicles if v.x < x_merge and v.v * 3.6 < SLOW_KMH)
            self.samples.append({"t": round(self.sim.time_s, 1), "mainline": slow + len(self.sim.mainline_queue),
                                 "ramp": len(self.sim.ramp_queue)})

    def _finished(self) -> bool:
        return self.sim.time_s >= float(self.sim.cfg["duration_s"]) - 1e-9

    def _advance_for_wall_time(self) -> None:
        now = time.monotonic()
        elapsed = min(max(now - self.last_wall_s, 0.0), 0.5)
        self.last_wall_s = now
        if not self.playing or self._finished():
            self.playing = False if self._finished() else self.playing
            return
        dt = float(self.sim.cfg["dt_s"])
        self.sim_time_credit_s += elapsed * self.speed
        steps = int(self.sim_time_credit_s / dt)
        self.sim_time_credit_s -= steps * dt
        for _ in range(steps):
            self._step()
            if self._finished():
                self.playing = False
                break

    def _extras(self) -> dict:
        """What the TMC sees and does, and the congestion rule at D1, for the side panel and charts."""
        sim, info = self.sim, self.info
        d1 = [r for r in sim.observation_rows if r["sensor_id"] == "D1"]
        d1_hist, run, best, since = [], 0, 0, None
        for r in d1:
            speed = r["mean_speed_mps"]
            slow = speed is not None and np.isfinite(speed) and speed * 3.6 < SLOW_KMH   # no crossing = not slow
            run = run + 1 if slow else 0
            if run >= 4 and since is None:
                since = r["interval_end_s"] - 4 * float(sim.cfg["detector_interval_s"])
            best = max(best, run)
            finite = speed is not None and np.isfinite(speed)
            d1_hist.append({"t": r["interval_end_s"], "speed_kmh": round(speed * 3.6, 1) if finite else None,
                            "occ": round(r["occupancy_pct"], 1) if np.isfinite(r["occupancy_pct"]) else None})
        meter_hist = [{"t": r["time_s"], "rate": r["rate_vph"], "occ": None if r["observed_occupancy_pct"] is None
                       or not np.isfinite(r["observed_occupancy_pct"]) else round(float(r["observed_occupancy_pct"]), 1),
                       "reason": r["reason"]} for r in sim.meter_rows]
        last = meter_hist[-1] if meter_hist else None
        metered = info["meter_mode"] != "unmetered"
        interval = 3600.0 / max(sim.meter.rate_vph, 1.0)
        green = (not metered) or (sim.time_s - (sim.meter.next_release_s - interval) < 1.0)
        lost = info["d2_lost_from_s"] is not None and sim.time_s >= info["d2_lost_from_s"]
        return {"case": info, "samples": self.samples, "d1": {"history": d1_hist, "slow_in_a_row": run,
                "congested": best >= 4, "since_s": since}, "tmc": {"metered": metered, "history": meter_hist,
                "rate_vph": sim.meter.rate_vph if metered else None, "last": last, "d2_lost": lost, "green": green}}

    def _payload(self) -> dict:
        state = self.sim.snapshot()
        state["session"] = {"playing": self.playing, "speed": self.speed, "case": self.case}
        state.update(self._extras())
        return state

    def state(self) -> dict:
        with self.lock:
            self._advance_for_wall_time()
            return self._payload()

    def control(self, request: dict) -> dict:
        with self.lock:
            action = request.get("action")
            if action == "play":
                if self._finished():
                    self.reset()
                self.playing = True
                self.last_wall_s = time.monotonic()
                self.sim_time_credit_s = 0.0
            elif action == "pause":
                self._advance_for_wall_time()
                self.playing = False
            elif action == "reset":
                self.reset(request.get("case"))
            elif action == "step":
                self.playing = False
                self._step()
            elif action == "speed":
                self._advance_for_wall_time()
                self.speed = min(max(float(request.get("value", 1.0)), 0.25), 20.0)
            elif action == "seek":
                target = min(max(float(request.get("time_s", 0.0)), 0.0), float(self.sim.cfg["duration_s"]))
                self.reset()
                while self.sim.time_s < target - 1e-9:
                    self._step()
                self.playing = False
            else:
                raise ValueError(f"Unknown action: {action}")
            return self._payload()


class AppHandler(SimpleHTTPRequestHandler):
    session: SimulationSession

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def log_message(self, format_string: str, *args) -> None:
        if self.path.startswith("/api/") and self.command == "GET":
            return
        super().log_message(format_string, *args)

    def _json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == "/api/config":
            self._json({"options": options(), "simulation": self.session.config["simulation"],
                        "cav": self.session.config["cav"], "ramp_meter": self.session.config["ramp_meter"]})
            return
        if self.path == "/api/state":
            self._json(self.session.state())
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/control":
            self._json({"error": "Not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length) or b"{}")
            self._json(self.session.control(request))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, 400)
        except Exception as exc:  # Keep browser errors readable during a live demo.
            self._json({"error": f"Simulation error: {exc}"}, 500)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CEE 281 live freeway visualization")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8781)
    parser.add_argument("--open", action="store_true", help="Open the dashboard in the default browser")
    args = parser.parse_args()

    config = json.loads((PROJECT_ROOT / "configs" / "scenarios.json").read_text(encoding="utf-8"))
    AppHandler.session = SimulationSession(config)
    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    url = f"http://{args.host}:{server.server_port}"
    print(f"CEE 281 live visualization: {url}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
