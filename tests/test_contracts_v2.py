"""Misma configuración entre editor futuro, motor, estrategia y reproducción."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.agents import create_policy
from sar_bot.core import RescueSimulation, Scenario
from sar_bot.ui.playback import prepare_episode


class ContractV2Tests(unittest.TestCase):
    def test_edited_scenario_object_is_executed_without_temporary_file(self):
        template = Scenario.load(ROOT / "scenarios/v2/building_10x10.json")
        custom = template.with_victims(((1, 0), (0, 1), (1, 1)))
        episode = prepare_episode(custom, "shortest")
        self.assertEqual(episode.scenario_id, custom.fingerprint())
        self.assertEqual(episode.configuration_id, custom.configuration_id)
        self.assertNotEqual(episode.scenario_id, template.fingerprint())
        self.assertEqual(episode.states[-1].outcome, "success")
        self.assertEqual(len(episode.states[-1].rescued), 3)

    def test_policy_factory_has_one_action_contract(self):
        scenario = Scenario.load(ROOT / "scenarios/v2/warmup_10x10.json")
        for strategy in ("shortest", "thermal", "random"):
            sim = RescueSimulation(scenario)
            action = create_policy(sim, strategy, seed=7).act(sim.state)
            self.assertIn(action, range(25))
        with self.assertRaises(ValueError):
            create_policy(sim, "unknown")
        with self.assertRaises(ValueError):
            create_policy(sim, "dqn")


if __name__ == "__main__":
    unittest.main()
