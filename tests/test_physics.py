"""
test_physics.py — Automated Sanity Checks for the Physics Engine
Run with:  pytest   or   python -m unittest discover tests
"""

import unittest
from src.physics import NoBubbleClinostatSim, SimConfig


class TestNoBubbleClinostat(unittest.TestCase):
    def test_incommensurate_rpms_zero_out_gravity(self):
        """3.00 / 2.61 RPM should average gravity well below 0.02g within 15 minutes."""
        sim = NoBubbleClinostatSim(SimConfig(rpm_frame=3.00, rpm_core=2.61))
        for _ in range(1800):  # 900 seconds = 15 min
            sim.step(0.5)
        self.assertLess(sim.g_avg_mag, 0.02)

    def test_equal_rpms_phase_lock_trap(self):
        """3.00 / 3.00 RPM phase-locks and leaves a huge residual gravity bias (>0.3g)."""
        sim = NoBubbleClinostatSim(SimConfig(rpm_frame=3.00, rpm_core=3.00))
        for _ in range(1800):
            sim.step(0.5)
        self.assertGreater(sim.g_avg_mag, 0.30)

    def test_degassed_shear_stays_below_neuromast_threshold(self):
        """At ~3 RPM in 2% methylcellulose without bubbles, larval shear stays ~10x-50x below RPM wall/bubble spikes."""
        sim = NoBubbleClinostatSim(SimConfig(rpm_frame=3.00, rpm_core=2.61, mc_percent=2.0))
        sim.step(1.0)
        self.assertLess(sim.shear_mpa, 20.0)
        self.assertLess(sim.slip_speed_ums, 5.0)


if __name__ == "__main__":
    unittest.main()
