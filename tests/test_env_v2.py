"""Perfiles de observación V2 y conservación del contrato histórico."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

try:
    from sar_bot.env import RescueEnv
except ImportError:
    HAS_RL = False
else:
    HAS_RL = True
    from sar_bot.core import Scenario


@unittest.skipUnless(HAS_RL, "Instalar extra rl")
class EnvV2Tests(unittest.TestCase):
    def scenario(self):
        return Scenario.load(ROOT / "scenarios/v2/warmup_10x10.json")

    def test_variable_count_observation_and_official_checkers(self):
        from gymnasium.utils.env_checker import check_env as check_gym
        from stable_baselines3.common.env_checker import check_env as check_sb3
        env = RescueEnv([self.scenario()], observation_mode="sensors")
        obs, _ = env.reset(seed=1)
        self.assertEqual(obs.shape, (302,))
        self.assertEqual(env.profile["victims"], 3)
        check_gym(env, skip_render_check=True)
        check_sb3(env)

    def test_edited_positions_are_validated_and_do_not_change_template(self):
        scenario = self.scenario()
        env = RescueEnv([scenario], observation_mode="sensors")
        obs, info = env.reset(seed=0, options={"victim_positions": [[2, 0], [0, 2], [2, 2]]})
        self.assertNotEqual(info["scenario_id"], scenario.fingerprint())
        self.assertEqual(env.scenarios[0].victims, ((1, 0), (0, 1), (1, 1)))
        self.assertTrue(env.observation_space.contains(obs))
        with self.assertRaises(ValueError):
            env.reset(options={"victim_positions": [[1, 0]]})

    def test_profile_rejects_mixed_counts_and_dimensions(self):
        with self.assertRaises(ValueError):
            RescueEnv([self.scenario(), self.scenario().with_victims([[1, 0], [0, 1]])])

    def test_potential_counts_repeated_returns_without_factorial_search(self):
        from sar_bot.core import MissionState, Robot
        env = RescueEnv([self.scenario()])
        env.reset()
        self.assertEqual(env._potential(env.simulation.state), -8)
        env.simulation.state = MissionState((Robot((1, 0), carrying=0), Robot((0, 1), carrying=1)))
        self.assertEqual(env._potential(env.simulation.state), -6)

    def test_bounded_guidance_does_not_reward_waiting_in_large_map(self):
        from sar_bot.env import RewardConfig
        scenario = Scenario.load(ROOT / "scenarios/v2/building_10x10.json")
        rewards = RewardConfig(potential_bound=40)
        env = RescueEnv([scenario], rewards, observation_mode="sensors")
        env.reset()
        self.assertGreaterEqual(env._potential(env.simulation.state), -40)
        _, reward, _, _, info = env.step(24)
        self.assertLess(reward, 0)
        self.assertEqual(info["reward_terms"]["pickup"], 0)
        self.assertEqual(info["reward_terms"]["delivery"], 0)

    def test_real_v2_model_profile_survives_save_load_and_blocks_wrong_map(self):
        import tempfile
        import torch
        from stable_baselines3 import DQN
        from sar_bot.agents.dqn import DQNPolicy
        from sar_bot.core import RescueSimulation
        torch.set_num_threads(1)
        env = RescueEnv([self.scenario()], observation_mode="sensors")
        model = DQN("MlpPolicy", env, seed=0, device="cpu", buffer_size=100,
                    learning_starts=4, batch_size=8, policy_kwargs={"net_arch": [16, 16]})
        model.sar_bot_profile = env.profile
        model.learn(total_timesteps=16)
        temporary_root = ROOT / "tmp/tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as directory:
            path = Path(directory) / "v2.zip"
            model.save(path)
            policy = DQNPolicy(RescueSimulation(self.scenario()), path)
            self.assertEqual(policy.model.sar_bot_profile, env.profile)
            self.assertIn(policy.act(policy.env.simulation.state), range(25))
            # Mismo número de celdas y tamaño de vector, pero geometría incompatible.
            other = Scenario("other", 20, 5, (0, 0), ((1, 0), (0, 1), (1, 1)),
                             frozenset(), ((25.,) * 20,) * 5)
            with self.assertRaises(ValueError):
                DQNPolicy(RescueSimulation(other), path)


if __name__ == "__main__":
    unittest.main()
