import math
import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cavsim.core import FreewaySimulation, Vehicle, idm_acceleration
from cavsim.metrics import count_error_veh, equilibrium_spacing_m, load_config, run_case, summarize


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.idm = self.config["human_idm"]
        self.v0 = self.config["simulation"]["free_speed_mps"]

    def test_idm_free_motion(self):
        """On an empty road a vehicle at rest accelerates at a."""
        vehicle = Vehicle("v", 0.0, 0.0, 0.0, "mainline", False, 0.0)
        self.assertAlmostEqual(idm_acceleration(vehicle, None, self.v0, self.idm, 5.0), self.idm["maximum_accel_mps2"])

    def test_idm_equilibrium(self):
        """At the equilibrium spacing s_e(v) and equal speeds the acceleration is zero."""
        v = 20.0
        spacing = float(equilibrium_spacing_m(np.array([v]), self.idm, 5.0, self.v0)[0])
        follower = Vehicle("f", 0.0, v, 0.0, "mainline", False, 0.0)
        leader = Vehicle("l", spacing, v, 0.0, "mainline", False, 0.0)
        self.assertAlmostEqual(idm_acceleration(follower, leader, self.v0, self.idm, 5.0), 0.0, places=6)

    def test_cav_short_gap_only_behind_cav(self):
        c = self.config
        sim = FreewaySimulation(c["simulation"], c["human_idm"], c["cav"], c["ramp_meter"], c["base_scenario"])
        cav, human = (Vehicle(n, 0.0, 10.0, 0.0, "mainline", flag, 0.0) for n, flag in (("c", True), ("h", False)))
        slot = Vehicle("zipper_slot", 100.0, 0.0, 0.0, "virtual", False, 0.0)
        self.assertEqual(sim._idm_cfg(cav, cav)["desired_time_gap_s"], c["cav"]["desired_time_gap_s"])
        for follower, leader in ((cav, human), (human, cav), (human, human), (cav, slot), (cav, None)):
            self.assertEqual(sim._idm_cfg(follower, leader)["desired_time_gap_s"], c["human_idm"]["desired_time_gap_s"])

    def test_base_case_conservation_detectors_no_collision(self):
        metric, tables, cfg = run_case(self.config)
        row = summarize(cfg, metric, tables)
        self.assertTrue(row["conservation_ok"])
        self.assertEqual(metric["overlap_steps"], 0)
        self.assertEqual(count_error_veh(tables["observations"], tables["crossings"]), 0)
        self.assertEqual(row["waiting_at_10min_veh"], 99)       # Run 4, seed 281 (Intermediate 2 result)

    def test_all_cav_no_collision(self):
        metric, tables, cfg = run_case(self.config, penetration=1.0)
        self.assertEqual(metric["overlap_steps"], 0)
        self.assertTrue(math.isfinite(metric["minimum_gap_m"]) and metric["minimum_gap_m"] > 0)


if __name__ == "__main__":
    unittest.main()
