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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = Path(__file__).resolve().parent / "web"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cavsim.core import FreewaySimulation


def all_scenarios(config: dict) -> list[dict]:
    """The six human runs (time gap T x ramp demand) and Run 4 with 50% and 100% CAVs, all with seed 281."""
    from cavsim.metrics import capacity_vph

    s = config["simulation"]
    cases = [(f"run_{n}", f"Run {n}", T, ramp, 0.0) for n, T, ramp in
             [(1, 0.8, 200.0), (2, 0.8, 700.0), (3, 1.0, 200.0), (4, 1.0, 700.0), (5, 1.2, 200.0), (6, 1.2, 700.0)]]
    cases += [("run_4_cav50", "Run 4 + 50% CAV", 1.0, 700.0, 0.5), ("run_4_cav100", "Run 4 + 100% CAV", 1.0, 700.0, 1.0)]
    runs = []
    for scenario_id, name, T, ramp, p in cases:
        cap = capacity_vph(dict(config["human_idm"], desired_time_gap_s=T), s["vehicle_length_m"], s["free_speed_mps"],
                           p, config["cav"]["desired_time_gap_s"])
        demand = config["base_scenario"]["mainline_demand_vph"] + ramp
        runs.append(dict(config["base_scenario"], scenario_id=scenario_id, desired_time_gap_s=T, ramp_demand_vph=ramp,
                         penetration=p, capacity_vph=round(cap),
                         label=f"{name} · T = {T} s · ramp {ramp:.0f} veh/h · demand {100 * demand / cap:.0f}% of capacity"))
    return runs


class SimulationSession:
    def __init__(self, config: dict):
        self.config = config
        self.scenarios = {item["scenario_id"]: item for item in all_scenarios(config)}
        self.scenario_id = "run_4"   # the run with the clearest stop-and-go waves
        self.speed = 1.0
        self.playing = False
        self.last_wall_s = time.monotonic()
        self.sim_time_credit_s = 0.0
        self.lock = threading.RLock()
        self.sim = self._new_sim(self.scenario_id)

    def _new_sim(self, scenario_id: str) -> FreewaySimulation:
        scenario = dict(self.scenarios[scenario_id])
        return FreewaySimulation(
            dict(self.config["simulation"]),
            dict(self.config["human_idm"], desired_time_gap_s=scenario["desired_time_gap_s"]),
            self.config["cav"],
            self.config["ramp_meter"],
            scenario,
        )

    def reset(self, scenario_id: str | None = None) -> None:
        if scenario_id is not None:
            if scenario_id not in self.scenarios:
                raise ValueError(f"Unknown scenario: {scenario_id}")
            self.scenario_id = scenario_id
        self.sim = self._new_sim(self.scenario_id)
        self.playing = False
        self.last_wall_s = time.monotonic()
        self.sim_time_credit_s = 0.0

    def _advance_for_wall_time(self) -> None:
        now = time.monotonic()
        elapsed = min(max(now - self.last_wall_s, 0.0), 0.5)
        self.last_wall_s = now
        finished = self.sim.time_s >= float(self.sim.cfg["duration_s"]) - 1e-9
        if not self.playing or finished:
            if finished:
                self.playing = False
            return
        dt = float(self.sim.cfg["dt_s"])
        self.sim_time_credit_s += elapsed * self.speed
        steps = int(self.sim_time_credit_s / dt)
        self.sim_time_credit_s -= steps * dt
        for _ in range(steps):
            self.sim.step()
            if self.sim.time_s >= float(self.sim.cfg["duration_s"]) - 1e-9:
                self.playing = False
                break

    def state(self) -> dict:
        with self.lock:
            self._advance_for_wall_time()
            state = self.sim.snapshot()
            state["session"] = {"playing": self.playing, "speed": self.speed}
            return state

    def control(self, request: dict) -> dict:
        with self.lock:
            action = request.get("action")
            if action == "play":
                if self.sim.snapshot()["finished"]:
                    self.reset()
                self.playing = True
                self.last_wall_s = time.monotonic()
                self.sim_time_credit_s = 0.0
            elif action == "pause":
                self._advance_for_wall_time()
                self.playing = False
            elif action == "toggle":
                self._advance_for_wall_time()
                self.playing = not self.playing
                self.last_wall_s = time.monotonic()
            elif action == "reset":
                self.reset(request.get("scenario_id"))
            elif action == "step":
                self.playing = False
                self.sim.step()
            elif action == "speed":
                self._advance_for_wall_time()
                value = float(request.get("value", 1.0))
                self.speed = min(max(value, 0.25), 20.0)
            elif action == "seek":
                target = min(max(float(request.get("time_s", 0.0)), 0.0), float(self.sim.cfg["duration_s"]))
                current_scenario = self.scenario_id
                self.reset(current_scenario)
                while self.sim.time_s < target - 1e-9:
                    self.sim.step()
                self.playing = False
            else:
                raise ValueError(f"Unknown action: {action}")
            state = self.sim.snapshot()
            state["session"] = {"playing": self.playing, "speed": self.speed}
            return state


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
            scenarios = []
            for item in all_scenarios(self.session.config):
                record = dict(item)
                record["label"] = item["label"]
                scenarios.append(record)
            self._json({
                "scenarios": scenarios,
                "simulation": self.session.config["simulation"],
                "cav": self.session.config["cav"],
            })
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
    parser.add_argument("--port", type=int, default=8765)
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
