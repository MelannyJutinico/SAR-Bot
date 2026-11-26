"""Restricciones contrastadas con el motor y con entrenamiento/carga reales."""

from pathlib import Path
import random
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import torch
from stable_baselines3 import DQN
from sar_bot.agents.masked_dqn import (MaskedDQN, MaskedDQNPolicy, joint_action_mask,
                                      RescueFeaturesExtractor)
from sar_bot.core import MissionState, Robot, Scenario
from sar_bot.core.simulation import OFFSETS
from sar_bot.env import RescueEnv


class MaskedDQNTests(unittest.TestCase):
    def test_all_actions_match_movement_rules_at_base_edges_and_random_positions(self):
        rng = random.Random(17)
        for path in ("coordination_hub_12x12.json", "thermal_detour_12x12.json"):
            scenario = Scenario.load(ROOT / "scenarios/v2" / path)
            env = RescueEnv([scenario], observation_mode="sensors")
            env.reset()
            walkable = [(x,y) for y in range(scenario.height) for x in range(scenario.width)
                        if scenario.walkable((x,y))]
            neighbor = next((scenario.base[0]+dx, scenario.base[1]+dy) for dx,dy in OFFSETS[:4]
                            if scenario.walkable((scenario.base[0]+dx, scenario.base[1]+dy)))
            positions = [(scenario.base, scenario.base), (scenario.base, neighbor)]
            positions += [tuple(rng.sample(walkable, 2)) for _ in range(40)]
            for pair in positions:
                env.simulation.state = MissionState(tuple(Robot(p) for p in pair))
                mask = joint_action_mask(torch.as_tensor(env.observation()), env.profile)[0].numpy()
                self.assertTrue(mask[24])
                for action in range(25):
                    intended = tuple((p[0]+OFFSETS[a][0], p[1]+OFFSETS[a][1])
                                     for p,a in zip(pair, (action//5, action%5)))
                    expected = (all(scenario.walkable(p) for p in intended)
                                and env.simulation.resolve_movement(pair, action) == intended)
                    self.assertEqual(bool(mask[action]), expected, (pair, action))

    def test_exploration_targets_and_saved_policy_all_respect_mask(self):
        torch.set_num_threads(1)
        scenario = Scenario.load(ROOT / "scenarios/v2/warmup_10x10.json")
        env = RescueEnv([scenario], observation_mode="sensors")
        model = MaskedDQN(MaskedDQNPolicy, env, seed=3, device="cpu", learning_starts=4,
                          batch_size=8, buffer_size=100, train_freq=4,
                          policy_kwargs={"net_arch": [16,16], "rescue_profile": env.profile})
        model.sar_bot_profile = env.profile
        model.learn(total_timesteps=32)
        self.assertGreater(model._n_updates, 0)
        buffer = model.replay_buffer
        observations = torch.as_tensor(buffer.observations[:buffer.size(), 0])
        masks = joint_action_mask(observations, env.profile).numpy()
        actions = buffer.actions[:buffer.size(), 0, 0]
        self.assertTrue(masks[np.arange(len(actions)), actions].all())
        values = model.q_net_target(observations).detach().numpy()
        self.assertTrue((values[~masks] == -1e9).all())
        temporary_root = ROOT / "tmp/tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as directory:
            path = Path(directory) / "masked.zip"
            model.save(path)
            obs, _ = env.reset()
            # El cargador DQN existente conserva la política y su máscara al inferir.
            loaded = DQN.load(path, device="cpu")
            self.assertEqual(int(model.predict(obs, deterministic=True)[0]),
                             int(loaded.predict(obs, deterministic=True)[0]))
            model = MaskedDQN.load(path, env=env, device="cpu")
            model.exploration_rate = 1
            valid = joint_action_mask(torch.as_tensor(obs), env.profile)[0].numpy()
            self.assertTrue(all(valid[int(model.predict(obs)[0])] for _ in range(100)))
            model.learn(total_timesteps=8, reset_num_timesteps=False)
            self.assertEqual(model.num_timesteps, 40)

    def test_compact_policy_uses_sensors_and_survives_standard_model_loader(self):
        torch.set_num_threads(1)
        scenario = Scenario.load(ROOT / "scenarios/v2/coordination_hub_12x12.json")
        env = RescueEnv([scenario], observation_mode="sensors")
        model = MaskedDQN(MaskedDQNPolicy, env, seed=0, device="cpu", learning_starts=4,
                          batch_size=8, buffer_size=100,
                          policy_kwargs={"net_arch": [16,16], "rescue_profile": env.profile,
                                         "features_extractor_class": RescueFeaturesExtractor,
                                         "features_extractor_kwargs": {"rescue_profile": env.profile}})
        model.sar_bot_profile = env.profile
        model.learn(total_timesteps=16)
        self.assertEqual(model.policy.q_net.features_dim, 102)
        obs, _ = env.reset()
        temporary_root = ROOT / "tmp/tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as directory:
            path = Path(directory) / "compact.zip"
            model.save(path)
            loaded = DQN.load(path, device="cpu")
            self.assertEqual(int(model.predict(obs, deterministic=True)[0]),
                             int(loaded.predict(obs, deterministic=True)[0]))
            from sar_bot.agents.dqn import DQNPolicy as RescuePolicy
            from sar_bot.core import RescueSimulation
            controller = RescuePolicy(RescueSimulation(scenario), path)
            self.assertEqual(controller.act(controller.env.simulation.state),
                             int(loaded.predict(obs, deterministic=True)[0]))


if __name__ == "__main__":
    unittest.main()
