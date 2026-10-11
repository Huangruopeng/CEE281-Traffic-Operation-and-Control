#!/usr/bin/env python3
"""Dependency-free local server for the CAV freeway live visualizer."""

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


def scenario_label(scenario: dict) -> str:
    controller = scenario["controller"].upper()
    penetration = int(round(100 * float(scenario["penetration"])))
    demand = "High demand" if scenario["demand"] == "high" else "Nominal demand"
    suffix = ""
    if scenario["scenario_id"].startswith("degraded"):
        suffix = " · degraded V2V"
    elif scenario["disturbance"] == "strong":
        suffix = " · strong brake"
    return f"{demand} · {controller} {penetration}%{suffix}"


class SimulationSession:
    def __init__(self, config: dict):
        self.config = config
        self.scenarios = {item["scenario_id"]: item for item in config["experiments"]}
        self.scenario_id = "nominal_cacc_50"
        self.speed = 1.0
        self.playing = False
        self.last_wall_s = time.monotonic()
        self.sim_time_credit_s = 0.0
        self.lock = threading.RLock()
        self.sim = self._new_sim(self.scenario_id)

    def _new_sim(self, scenario_id: str) -> FreewaySimulation:
        return FreewaySimulation(
            dict(self.config["simulation"]),
            self.config["human_idm"],
            self.config["automated_controller"],
            self.config["ramp_meter"],
            dict(self.scenarios[scenario_id]),
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
            for item in self.session.config["experiments"]:
                record = dict(item)
                record["label"] = scenario_label(item)
                scenarios.append(record)
            self._json({
                "scenarios": scenarios,
                "simulation": self.session.config["simulation"],
                "controller": self.session.config["automated_controller"],
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
