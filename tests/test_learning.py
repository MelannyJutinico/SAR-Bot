"""Entrenamiento breve real y carga de una política; no comprueba convergencia."""

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

try:
    import torch
    from stable_baselines3 import DQN
except ImportError:
    HAS_RL = False
else:
    HAS_RL = True
    import numpy as np
    from sar_bot.core import Scenario
    from sar_bot.env import RescueEnv
    from sar_bot.learning import evaluate_model, model_score


@unittest.skipUnless(HAS_RL, "Instalar el extra rl para verificar DQN")
class LearningTests(unittest.TestCase):
    def test_train_save_load_and_evaluate_real_dqn(self):
        torch.set_num_threads(1)
        scenario = Scenario.load(ROOT / "scenarios/curriculum/warmup.json")
        env = RescueEnv([scenario])
        model = DQN("MlpPolicy", env, seed=0, device="cpu", buffer_size=100,
                    learning_starts=8, batch_size=8, train_freq=4,
                    policy_kwargs={"net_arch": [16, 16]})
        model.learn(total_timesteps=32)
        self.assertEqual(model.num_timesteps, 32)
        observation, _ = env.reset(seed=0)
        action_before, _ = model.predict(observation, deterministic=True)
        temporary_root = ROOT / "tmp" / "tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as directory:
            path = Path(directory) / "model.zip"
            model.save(path)
            loaded = DQN.load(path, device="cpu")
            action_after, _ = loaded.predict(observation, deterministic=True)
            np.testing.assert_equal(action_before, action_after)
            result = evaluate_model(loaded, [scenario])[0]
            self.assertIn(result["outcome"], ("success", "destroyed", "time_limit"))
            self.assertLessEqual(result["steps"], scenario.max_steps)
            self.assertEqual(result["strategy"], "dqn")
            self.assertTrue(np.isfinite(result["return"]))
            from sar_bot.agents.dqn import DQNPolicy
            from sar_bot.core import RescueSimulation
            simulation = RescueSimulation(scenario)
            policy = DQNPolicy(simulation, path)
            self.assertEqual(policy.act(simulation.state), int(action_after))
            before = simulation.snapshot()
            policy.act(simulation.state)
            self.assertEqual(before, simulation.snapshot())
        env.close()

    def test_selection_prioritizes_mission_over_return(self):
        successful = [{"success": True, "rescued": 2, "return": 5}]
        incomplete = [{"success": False, "rescued": 1, "return": 1000}]
        self.assertGreater(model_score(successful), model_score(incomplete))


if __name__ == "__main__":
    unittest.main()
