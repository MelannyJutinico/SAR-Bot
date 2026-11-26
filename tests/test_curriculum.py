"""La simplificación de objetivos pertenece solo al entrenamiento."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np
from sar_bot.agents import create_policy
from sar_bot.core import Scenario
from sar_bot.env import RescueEnv, RewardConfig
from sar_bot.env.curriculum import CurriculumRescueEnv


class CurriculumTests(unittest.TestCase):
    def setUp(self):
        self.scenario = Scenario.load(ROOT / "scenarios/v2/warmup_10x10.json")

    def test_seeded_initial_deliveries_are_observed_without_changing_template(self):
        env = CurriculumRescueEnv([self.scenario], pending_victims=1)
        first, info = env.reset(seed=17)
        second, again = env.reset(seed=17)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(info["rescued"], again["rescued"])
        self.assertEqual(len(info["rescued"]), 2)
        self.assertEqual(env.profile["victims"], 3)
        standard = RescueEnv([self.scenario], observation_mode="sensors")
        _, original = standard.reset(seed=17)
        self.assertEqual(original["rescued"], [])

    def test_remaining_delivery_is_real_and_initial_ones_are_not_rewarded_again(self):
        env = CurriculumRescueEnv([self.scenario], RewardConfig(gamma=1), pending_victims=1)
        env.reset(seed=0)
        policy = create_policy(env.simulation, "shortest")
        pickup = delivery = 0
        while env.simulation.state.outcome == "running":
            _, _, _, _, info = env.step(policy.act(env.simulation.state))
            pickup += info["reward_terms"]["pickup"]
            delivery += info["reward_terms"]["delivery"]
        self.assertTrue(info["is_success"])
        self.assertEqual(pickup, 5)
        self.assertEqual(delivery, 50)

    def test_full_curriculum_matches_normal_reset_and_invalid_counts_rejected(self):
        env = CurriculumRescueEnv([self.scenario], pending_victims=3)
        normal = RescueEnv([self.scenario], observation_mode="sensors")
        first, info = env.reset(seed=2)
        second, expected = normal.reset(seed=2)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(info, expected)
        for count in (0, 4, True):
            with self.assertRaises(ValueError):
                CurriculumRescueEnv([self.scenario], pending_victims=count)


if __name__ == "__main__":
    unittest.main()
