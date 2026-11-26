"""Rescates múltiples y caché de planes en edificios mayores."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.agents import ShortestPathPolicy, ThermalPathPolicy
from sar_bot.core import RescueSimulation, Scenario
from sar_bot.evaluation import evaluate_episode


class ReferenceV2Tests(unittest.TestCase):
    def test_ten_by_ten_three_victims_and_multiple_trips(self):
        scenario = Scenario.load(ROOT / "scenarios/v2/building_10x10.json")
        for policy_class in (ShortestPathPolicy, ThermalPathPolicy):
            with self.subTest(policy=policy_class.__name__):
                sim = RescueSimulation(scenario)
                policy = policy_class(sim)
                result = evaluate_episode(sim, policy, policy_class.__name__)
                self.assertTrue(result["success"])
                self.assertEqual(result["rescued"], 3)
                self.assertEqual(result["victims_total"], 3)
                self.assertLess(result["replans"], result["steps"])
                self.assertGreater(result["expanded_states"], 0)

    def test_assignments_wait_until_a_robot_is_available(self):
        scenario = Scenario.load(ROOT / "scenarios/v2/building_10x10.json")
        sim = RescueSimulation(scenario)
        policy = ShortestPathPolicy(sim)
        self.assertEqual(len(set(policy.targets(sim.state))), 2)
        self.assertEqual(len(policy.assignments), 2)
        before = sim.snapshot()
        policy.act(sim.state)
        self.assertEqual(before, sim.snapshot())


if __name__ == "__main__":
    unittest.main()
