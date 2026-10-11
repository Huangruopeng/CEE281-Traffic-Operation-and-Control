import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cavsim.core import FreewaySimulation, Vehicle, idm_acceleration
from cavsim.observation import audit_detector_counts


class ProjectChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "configs" / "scenarios.json").read_text())

    def test_idm_free_motion(self):
        v = Vehicle("x", 0.0, 0.0, 0.0, "test", False, "human", 0.0)
        a = idm_acceleration(v, None, 30.0, self.config["human_idm"], 5.0)
        self.assertAlmostEqual(a, self.config["human_idm"]["maximum_accel_mps2"], places=8)

    def test_idm_equilibrium(self):
        cfg = self.config["human_idm"]
        speed = 15.0
        desired = cfg["minimum_gap_m"] + speed * cfg["desired_time_gap_s"]
        free = 1.0 - (speed / 30.0) ** cfg["accel_exponent"]
        equilibrium_gap = desired / math.sqrt(free)
        leader = Vehicle("lead", equilibrium_gap + 5.0, speed, 0.0, "test", False, "human", 0.0)
        follower = Vehicle("follow", 0.0, speed, 0.0, "test", False, "human", 0.0)
        a = idm_acceleration(follower, leader, 30.0, cfg, 5.0)
        self.assertAlmostEqual(a, 0.0, places=7)

    def test_minimum_case_conservation_and_detector_audit(self):
        sim_cfg = dict(self.config["simulation"])
        sim_cfg.update({"duration_s": 90.0, "demand_end_s": 45.0, "initial_platoon_size": 5})
        scenario = dict(self.config["experiments"][0])
        sim = FreewaySimulation(sim_cfg, self.config["human_idm"], self.config["automated_controller"], self.config["ramp_meter"], scenario)
        metric = sim.run()
        tables = sim.tables()
        accounted = metric["exited_vehicles"] + metric["unfinished_vehicles"]
        self.assertEqual(metric["generated_vehicles"], accounted)
        # Human drivers are pure IDM (no position guard), so check that no vehicles overlap.
        self.assertEqual(metric["overlap_steps"], 0)
        self.assertGreater(metric["minimum_gap_m"], 0.0)
        audit = audit_detector_counts(tables["observations"], tables["crossings"], sample_intervals=3)
        self.assertTrue((audit["count_error_veh"] == 0).all())

    def test_live_step_and_snapshot_interface(self):
        sim_cfg = dict(self.config["simulation"])
        sim_cfg.update({"duration_s": 20.0, "demand_end_s": 10.0})
        scenario = dict(next(item for item in self.config["experiments"] if item["scenario_id"] == "nominal_cacc_50"))
        sim = FreewaySimulation(sim_cfg, self.config["human_idm"], self.config["automated_controller"], self.config["ramp_meter"], scenario)
        before = sim.snapshot()
        sim.step()
        after = sim.snapshot()
        self.assertEqual(before["time_s"], 0.0)
        self.assertAlmostEqual(after["time_s"], sim_cfg["dt_s"])
        self.assertEqual(after["scenario_id"], scenario["scenario_id"])
        self.assertIn("control_state", after["vehicles"][0])
        self.assertIn("age_since_spawn_s", after["vehicles"][0])
        self.assertIn("meter_rate_vph", after["metrics"])
        self.assertEqual(len(after["detectors"]), len(sim_cfg["detector_positions_m"]))

    def test_safety_supervisor_enforces_physical_clearance(self):
        sim_cfg = dict(self.config["simulation"])
        sim_cfg.update({"duration_s": 20.0, "demand_end_s": 10.0})
        scenario = dict(self.config["experiments"][2])
        sim = FreewaySimulation(sim_cfg, self.config["human_idm"], self.config["automated_controller"], self.config["ramp_meter"], scenario)
        for _ in range(int(sim_cfg["duration_s"] / sim_cfg["dt_s"])):
            sim.step()
        self.assertGreaterEqual(sim.global_min_gap_m, sim_cfg["minimum_physical_gap_m"] - 1e-9)
        self.assertTrue(all(not vehicle.collision_guard_active or vehicle.min_gap_m >= sim_cfg["minimum_physical_gap_m"] - 1e-9 for vehicle in sim.vehicles))


if __name__ == "__main__":
    unittest.main()

