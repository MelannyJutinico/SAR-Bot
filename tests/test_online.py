"""Sesiones: experiencias reales, continuidad, deduplicación y recuperación."""

from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import torch
from sar_bot.agents.masked_dqn import MaskedDQN, MaskedDQNPolicy
from sar_bot.core import Scenario
from sar_bot.env import RescueEnv, RewardConfig
from sar_bot.online import LearningSession, SessionSettings, digest, session_lock


class OnlineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        root = ROOT / "tmp/tests"
        root.mkdir(parents=True, exist_ok=True)
        cls.source = tempfile.TemporaryDirectory(dir=root)
        cls.base = Path(cls.source.name) / "model.zip"
        original = Scenario.load(ROOT / "scenarios/v2/warmup_10x10.json")
        cls.scenario = replace(original.with_victims(((8,1),(1,8),(8,8))), max_steps=8)
        rewards = RewardConfig(gamma=1)
        env = RescueEnv([cls.scenario], rewards, observation_mode="sensors")
        model = MaskedDQN(MaskedDQNPolicy, env, seed=0, device="cpu", learning_starts=4,
                          batch_size=8, buffer_size=64, train_freq=4,
                          policy_kwargs={"net_arch":[16,16],"rescue_profile":env.profile})
        model.sar_bot_profile = env.profile
        model.learn(total_timesteps=16)
        model.save(cls.base)
        (cls.base.parent / "metadata.json").write_text(json.dumps({
            "rewards":asdict(rewards),"config":{"mask_invalid_actions":True},
            "observation_profile":env.profile}),encoding="utf-8")
        cls.settings = SessionSettings(capacity=32, exploration=1)
        cls.base_hash = digest(cls.base)

    @classmethod
    def tearDownClass(cls):
        cls.source.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "tmp/tests")
        self.directory = Path(self.temporary.name) / "session"
        self.session = LearningSession(self.directory, self.base, settings=self.settings)

    def tearDown(self):
        self.temporary.cleanup()

    def test_prepare_does_not_train_and_completed_mission_changes_weights(self):
        episode = self.session.prepare_episode(self.scenario)
        self.assertIsNotNone(episode.learning_id)
        self.assertFalse((self.directory / "current.json").exists())
        before = self.session.snapshot()
        original, env = self.session._model(before, self.scenario)
        weights = [p.detach().clone() for p in original.policy.parameters()]
        result = self.session.learn_episode(episode)
        self.assertEqual(result["missions"],1)
        self.assertEqual(result["transitions"],8)
        self.assertGreater(result["updates"],0)
        self.assertEqual(result["buffer_size"],8)
        snapshot = self.session.snapshot()
        learned, _ = self.session._model(snapshot,self.scenario,replay=True)
        self.assertTrue(any(not torch.equal(a,b) for a,b in zip(weights,learned.policy.parameters())))
        self.assertEqual(learned.replay_buffer.timeouts[7,0],1)
        self.assertEqual(learned.replay_buffer.dones[7,0],1)
        self.assertEqual(digest(self.base),self.base_hash)

    def test_restart_preserves_memory_updates_and_episode_deduplication(self):
        episode = self.session.prepare_episode(self.scenario)
        first = self.session.learn_episode(episode)
        resumed = LearningSession(self.directory,self.base,settings=self.settings)
        with patch.object(resumed,"_model",side_effect=AssertionError("No entrenar una repeticion")):
            duplicate = resumed.learn_episode(episode)
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["updates"],first["updates"])
        next_episode = resumed.prepare_episode(self.scenario)
        self.assertNotEqual(next_episode.learning_id,episode.learning_id)
        second = resumed.learn_episode(next_episode)
        self.assertEqual(second["missions"],2)
        self.assertEqual(second["buffer_size"],16)
        self.assertEqual(second["transitions"],16)
        self.assertGreater(second["updates"],first["updates"])
        model,_ = resumed._model(resumed.snapshot(),self.scenario,replay=True)
        self.assertEqual(model.num_timesteps,second["model_timesteps"])
        self.assertEqual(model.replay_buffer.size(),16)

    def test_recover_previous_checkpoint_if_current_file_is_corrupt(self):
        for _ in range(2):
            self.session.learn_episode(self.session.prepare_episode(self.scenario))
        current = self.session.snapshot()
        current.model_path.write_bytes(b"checkpoint interrumpido")
        recovered = self.session.snapshot()
        self.assertTrue(recovered.recovered)
        self.assertEqual(recovered.metadata["missions"],1)
        result = self.session.learn_episode(self.session.prepare_episode(self.scenario))
        self.assertTrue(result["recovered"])
        self.assertEqual(self.session.snapshot().metadata["missions"],2)

    def test_failed_publication_keeps_prior_generation(self):
        self.session.learn_episode(self.session.prepare_episode(self.scenario))
        from sar_bot.online import atomic_json
        def fail(path,data):
            if Path(path).name=="current.json":raise OSError("corte simulado")
            return atomic_json(path,data)
        episode = self.session.prepare_episode(self.scenario)
        with patch("sar_bot.online.atomic_json",side_effect=fail):
            with self.assertRaises(OSError):self.session.learn_episode(episode)
        self.assertEqual(self.session.snapshot().metadata["missions"],1)

    def test_lock_profile_guard_and_reserved_cases(self):
        with session_lock(self.directory):
            with self.assertRaises(RuntimeError):self.session.snapshot()
        other = Scenario.load(ROOT / "scenarios/v2/coordination_hub_12x12.json")
        with self.assertRaises(ValueError):self.session.prepare_episode(other)
        reserved = LearningSession(self.directory,self.base,settings=self.settings,
                                   protected_ids={self.scenario.scenario_id})
        with self.assertRaisesRegex(ValueError,"reservada"):
            reserved.prepare_episode(self.scenario)

    def test_history_replay_and_unfinished_missions_do_not_train(self):
        episode = self.session.prepare_episode(self.scenario)
        with self.assertRaises(ValueError):self.session.learn_episode(replace(episode,learning_id=None))
        with self.assertRaises(ValueError):self.session.learn_episode(replace(
            episode,states=episode.states[:-1],actions=episode.actions[:-1]))
        self.assertEqual(self.session.snapshot().metadata["missions"],0)

    def test_capacity_and_generation_retention_are_bounded(self):
        for _ in range(5):
            result = self.session.learn_episode(self.session.prepare_episode(self.scenario))
        self.assertEqual(result["transitions"],40)
        self.assertEqual(result["buffer_size"],32)
        self.assertEqual(len(list(self.directory.glob("g-*"))),3)
        loaded,_ = self.session._model(self.session.snapshot(),self.scenario,replay=True)
        optimizer_steps = [int(s["step"].item()) for s in loaded.policy.optimizer.state.values() if "step" in s]
        self.assertTrue(optimizer_steps)
        self.assertEqual(max(optimizer_steps),loaded._n_updates)


if __name__ == "__main__":
    unittest.main()
