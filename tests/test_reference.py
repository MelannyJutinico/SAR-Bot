"""Pruebas de navegación y de la medición de referencias."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.agents import RandomPolicy, ShortestPathPolicy
from sar_bot.agents.reference import shortest_distance
from sar_bot.core import Action, MissionState, RescueSimulation, Robot, Scenario
from sar_bot.evaluation import evaluate_episode


class ReferenceTests(unittest.TestCase):
    def simulation(self, filename="demo.json"):
        return RescueSimulation(Scenario.load(ROOT / "scenarios" / filename))

    def test_assignment_is_distinct_and_stable(self):
        sim = self.simulation()
        policy = ShortestPathPolicy(sim)
        goals = policy.targets(sim.state)
        self.assertEqual(set(goals), set(sim.scenario.victims))
        sim.step(policy.act(sim.state))
        self.assertEqual(policy.targets(sim.state), goals)

    def test_demo_completed_without_script(self):
        sim = self.simulation()
        result = evaluate_episode(sim, ShortestPathPolicy(sim), "shortest")
        self.assertTrue(result["success"])
        self.assertEqual(result["rescued"], 2)
        self.assertEqual(result["steps"], 10)
        self.assertEqual(result["damage_total"], 18)
        self.assertEqual(result["planning_failures"], 0)

    def test_shared_exit_requires_one_robot_to_wait(self):
        sim = self.simulation("pasillo_compartido.json")
        policy = ShortestPathPolicy(sim)
        action = policy.act(sim.state)
        first, second = sim.decode_action(action)
        self.assertIn(Action.WAIT, (first, second))
        result = evaluate_episode(sim, policy, "shortest")
        self.assertTrue(result["success"])
        self.assertEqual(result["planning_failures"], 0)

    def test_reference_does_not_consider_temperature(self):
        # Geometría idéntica y calor distinto deben producir las mismas acciones.
        cold, hot = self.simulation(), self.simulation("ruta_caliente.json")
        policies = ShortestPathPolicy(cold), ShortestPathPolicy(hot)
        while cold.state.outcome == hot.state.outcome == "running":
            first, second = policies[0].act(cold.state), policies[1].act(hot.state)
            self.assertEqual(first, second)
            cold.step(first)
            hot.step(second)

    def test_obstacles_change_path_distance(self):
        scenario = self.simulation("pasillo_compartido.json").scenario
        self.assertEqual(shortest_distance(scenario, (1, 2), (3, 2)), 4)

    def test_carried_victim_not_reassigned(self):
        sim = self.simulation()
        sim.state = MissionState((Robot((5, 0), carrying=0), Robot((0, 1))))
        policy = ShortestPathPolicy(sim)
        self.assertEqual(policy.targets(sim.state), (sim.scenario.base, sim.scenario.victims[1]))

    def test_random_seed_is_reproducible(self):
        results = []
        for _ in range(2):
            sim = self.simulation()
            results.append(evaluate_episode(sim, RandomPolicy(sim, 19), "random", 19))
        self.assertEqual(results[0], results[1])

    def test_planning_does_not_advance_time_or_damage(self):
        sim = self.simulation()
        before = sim.snapshot()
        ShortestPathPolicy(sim).act(sim.state)
        self.assertEqual(before, sim.snapshot())

    def test_evaluation_stops_at_limit(self):
        from dataclasses import replace
        sim = RescueSimulation(replace(self.simulation().scenario, max_steps=1))
        result = evaluate_episode(sim, RandomPolicy(sim, 0), "random", 0)
        self.assertEqual(result["steps"], 1)
        self.assertEqual(result["outcome"], "time_limit")
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
