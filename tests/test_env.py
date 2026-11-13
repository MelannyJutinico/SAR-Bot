"""Contrato Gymnasium y vínculo entre recompensas y misión real."""

from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

try:
    import gymnasium
    import numpy as np
except ImportError:
    HAS_RL = False
else:
    HAS_RL = True
    from sar_bot.env import RescueEnv
    from sar_bot.core import Action, Scenario


@unittest.skipUnless(HAS_RL, "Instalar el extra rl para verificar Gymnasium")
class EnvTests(unittest.TestCase):
    def scenario(self):
        return Scenario.load(ROOT / "scenarios/demo.json")

    def test_official_gymnasium_checker(self):
        from gymnasium.utils.env_checker import check_env
        check_env(RescueEnv([self.scenario()]), skip_render_check=True)

    def test_official_sb3_checker(self):
        from stable_baselines3.common.env_checker import check_env
        check_env(RescueEnv([self.scenario()]))

    def test_observation_covers_carrying_and_delivered_state(self):
        env = RescueEnv([self.scenario()])
        obs, _ = env.reset(seed=0)
        self.assertEqual(obs.shape, (97,))
        self.assertEqual(obs.dtype, np.float32)
        for action in [16] * 5 + [10] * 5:
            obs, reward, terminated, truncated, info = env.step(action)
            self.assertTrue(env.observation_space.contains(obs))
            self.assertEqual(reward, sum(info["reward_terms"].values()))
        self.assertTrue(terminated)
        self.assertFalse(truncated)
        self.assertTrue(info["is_success"])
        self.assertEqual(info["rescued"], [0, 1])
        self.assertEqual(info["reward_terms"]["delivery"], 100)
        with self.assertRaises(RuntimeError):
            env.step(24)

    def test_timeout_is_not_termination(self):
        env = RescueEnv([replace(self.scenario(), max_steps=1)])
        env.reset(seed=0)
        _, _, terminated, truncated, info = env.step(np.int64(24))
        self.assertFalse(terminated)
        self.assertTrue(truncated)
        self.assertFalse(info["is_success"])
        self.assertEqual(info["reward_terms"]["terminal"], -20)

    def test_thermal_penalty_uses_damage_of_both_robots(self):
        env = RescueEnv([self.scenario()])
        env.reset(seed=0)
        env.step(16)
        _, _, _, _, info = env.step(16)
        self.assertEqual(info["reward_terms"]["damage"], -2)

    def test_sampling_scenarios_is_seeded(self):
        env = RescueEnv([self.scenario(), replace(self.scenario(), name="other")])
        first, info1 = env.reset(seed=17)
        second, info2 = env.reset(seed=17)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(info1, info2)
        _, info = env.reset(options={"scenario_index": 1})
        self.assertEqual(info["scenario"], "other")

    def test_invalid_action_does_not_change_state(self):
        env = RescueEnv([self.scenario()])
        env.reset()
        before = env.simulation.snapshot()
        for action in (True, -1, 25, 1.5):
            with self.assertRaises(ValueError):
                env.step(action)
        self.assertEqual(before, env.simulation.snapshot())

    def test_local_sensors_expose_legal_moves_heat_and_goal_distances(self):
        env = RescueEnv([self.scenario()], observation_mode="sensors")
        obs, _ = env.reset(seed=0)
        self.assertEqual(obs.shape, (157,))
        self.assertTrue(env.observation_space.contains(obs))
        # Sensores: 6 valores por acción, primero robot 0, orden UP/DOWN/LEFT/RIGHT/WAIT.
        up = obs[97:103]
        right = obs[97 + 3 * 6:97 + 4 * 6]
        self.assertEqual(up[0], 0)
        np.testing.assert_allclose(right, [1, 0, 30 / 200, 1 / 36, 4 / 36, 6 / 36])

    def test_sensor_mode_passes_both_official_checkers(self):
        from gymnasium.utils.env_checker import check_env as check_gym
        from stable_baselines3.common.env_checker import check_env as check_sb3
        env = RescueEnv([self.scenario()], observation_mode="sensors")
        check_gym(env, skip_render_check=True)
        check_sb3(env)


if __name__ == "__main__":
    unittest.main()
