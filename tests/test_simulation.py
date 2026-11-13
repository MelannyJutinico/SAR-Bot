"""Verificaciones del contrato del simulador, sin dependencias externas."""

from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.core import Action as A, MissionState, RescueSimulation, Robot, Scenario, damage_rate


def scenario_with(temperatures=None, max_steps=100, walls=frozenset()):
    if temperatures is None:
        temperatures = ((25.,) * 3,) * 3
    return Scenario("test", 3, 3, (0, 0), ((2, 0), (0, 2)), walls,
                    temperatures, max_steps)


class SimulationTests(unittest.TestCase):
    def step(self, sim, first=A.WAIT, second=A.WAIT):
        return sim.step(sim.encode_actions(first, second))

    def test_temperature_boundaries(self):
        for temperature, damage in [(20, 0), (39.9, 0), (40, 2), (59.9, 2),
                                    (60, 5), (79.9, 5), (80, 10), (100, 10)]:
            with self.subTest(temperature=temperature):
                self.assertEqual(damage_rate(temperature), damage)

    def test_waiting_exposes_both_once_each_step(self):
        sim = RescueSimulation(scenario_with(((25, 65, 25), (65, 25, 25), (25, 25, 25))))
        sim.state = MissionState((Robot((1, 0)), Robot((0, 1))))
        for _ in range(4):
            self.step(sim)
        self.assertEqual([r.integrity for r in sim.state.robots], [80, 80])
        self.assertEqual([r.damage for r in sim.state.robots], [20, 20])
        self.assertEqual(sim.state.steps, 4)

    def test_wall_and_boundary_still_consume_time_and_heat(self):
        sim = RescueSimulation(scenario_with(((25, 65, 25), (25, 25, 25), (25, 25, 25)),
                                            walls=frozenset({(1, 1)})))
        sim.state = MissionState((Robot((1, 0)), Robot((0, 0))))
        state = self.step(sim, A.DOWN, A.UP)
        self.assertEqual(state.robots[0].position, (1, 0))
        self.assertEqual(state.robots[0].integrity, 95)
        self.assertEqual(state.steps, 1)

    def test_same_destination_blocks_both(self):
        sim = RescueSimulation(scenario_with())
        sim.state = MissionState((Robot((0, 1)), Robot((2, 1))))
        state = self.step(sim, A.RIGHT, A.LEFT)
        self.assertEqual([r.position for r in state.robots], [(0, 1), (2, 1)])

    def test_swap_blocks_both(self):
        sim = RescueSimulation(scenario_with())
        sim.state = MissionState((Robot((0, 1)), Robot((1, 1))))
        state = self.step(sim, A.RIGHT, A.LEFT)
        self.assertEqual([r.position for r in state.robots], [(0, 1), (1, 1)])

    def test_occupied_cell_blocks_incoming_robot(self):
        sim = RescueSimulation(scenario_with())
        sim.state = MissionState((Robot((0, 1)), Robot((1, 1))))
        state = self.step(sim, A.RIGHT, A.WAIT)
        self.assertEqual(state.robots[0].position, (0, 1))

    def test_can_follow_into_vacated_cell(self):
        sim = RescueSimulation(scenario_with())
        sim.state = MissionState((Robot((0, 1)), Robot((1, 1))))
        state = self.step(sim, A.RIGHT, A.RIGHT)
        self.assertEqual([r.position for r in state.robots], [(1, 1), (2, 1)])

    def test_complete_rescue_on_last_allowed_step(self):
        sim = RescueSimulation(scenario_with(max_steps=4))
        for actions in [(A.RIGHT, A.DOWN)] * 2 + [(A.LEFT, A.UP)] * 2:
            state = self.step(sim, *actions)
        self.assertEqual(state.outcome, "success")
        self.assertEqual(state.rescued, frozenset({0, 1}))
        self.assertTrue(state.terminated)
        self.assertFalse(state.truncated)
        self.assertEqual([r.position for r in state.robots], [(0, 0), (0, 0)])
        self.assertEqual([r.carrying for r in state.robots], [None, None])
        with self.assertRaises(RuntimeError):
            self.step(sim)

    def test_destruction_prevents_pickup_and_delivery_in_same_step(self):
        sim = RescueSimulation(scenario_with(((25, 80, 25), (25, 25, 25), (25, 25, 25))))
        sim.state = MissionState((Robot((1, 0), 5), Robot((0, 1), carrying=1)))
        state = self.step(sim, A.WAIT, A.UP)
        self.assertEqual(state.outcome, "destroyed")
        self.assertEqual(state.robots[0].integrity, 0)
        self.assertEqual(state.robots[0].damage, 5)
        self.assertEqual(state.rescued, frozenset())

    def test_waiting_on_victim_does_not_duplicate_pickup(self):
        sim = RescueSimulation(scenario_with())
        self.step(sim, A.RIGHT)
        self.step(sim, A.RIGHT)
        self.step(sim)
        self.assertEqual([r.carrying for r in sim.state.robots], [0, None])
        self.assertEqual(len(sim.state.rescued), 0)

    def test_time_limit_is_truncation(self):
        sim = RescueSimulation(scenario_with(max_steps=1))
        state = self.step(sim)
        self.assertEqual(state.outcome, "time_limit")
        self.assertTrue(state.truncated)
        self.assertFalse(state.terminated)

    def test_reset_restores_episode(self):
        sim = RescueSimulation(scenario_with())
        initial = sim.snapshot()
        self.step(sim, A.RIGHT, A.DOWN)
        sim.reset()
        self.assertEqual(sim.snapshot(), initial)

    def test_invalid_action_does_not_advance_time(self):
        sim = RescueSimulation(scenario_with())
        for action in (-1, 25, 1.5, True):
            with self.assertRaises(ValueError):
                sim.step(action)
        self.assertEqual(sim.state.steps, 0)

    def test_scenario_validation(self):
        scenario = scenario_with()
        for changes in [dict(temperatures=((25,),)), dict(base=(1, 4)),
                        dict(victims=((1, 1), (1, 1))),
                        dict(walls=frozenset({(1, 0), (0, 1)}))]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(scenario, **changes)

    def test_demo_has_a_feasible_complete_mission(self):
        sim = RescueSimulation(Scenario.load(ROOT / "scenarios" / "demo.json"))
        for actions in [(A.RIGHT, A.DOWN)] * 5 + [(A.LEFT, A.UP)] * 5:
            self.step(sim, *actions)
        self.assertEqual(sim.state.outcome, "success")
        self.assertGreater(sim.state.robots[0].damage, 0)
        self.assertEqual(sim.state.steps, 10)


if __name__ == "__main__":
    unittest.main()
