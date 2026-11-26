"""Misiones de aprendizaje, reproducción y reinicio de la interfaz."""

from concurrent.futures import Future
from dataclasses import replace
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
os.environ["SDL_VIDEODRIVER"]="dummy"
import pygame
from sar_bot.core import Scenario
from sar_bot.online import LearningSession, digest
from sar_bot.ui.app import RescueApp


class OnlineUITests(unittest.TestCase):
    def setUp(self):
        root = ROOT/"tmp/tests"
        root.mkdir(parents=True,exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(dir=root)
        self.root=Path(self.temporary.name)
        folder=self.root/"scenarios/v2";folder.mkdir(parents=True)
        scenario=replace(Scenario.load(ROOT/"scenarios/v2/coordination_hub_12x12.json"),max_steps=8)
        self.path=folder/"mission.json";scenario.save(self.path)
        self.model=ROOT/"artifacts/v2_12x12/model.zip"
        self.original_hash=digest(self.model)
        pygame.display.init();pygame.font.init()
        self.app=self.make_app()

    def make_app(self):
        return RescueApp(self.root,self.path,"dqn",self.model,0,asynchronous=False)

    def tearDown(self):
        self.app.close();pygame.quit();self.temporary.cleanup()

    def finish(self):
        while not self.app.playback.finished:self.app.playback.step()
        self.app.update(0)
        self.app.wait_for_learning()
        self.app.update(0)

    def test_learning_is_once_per_new_mission_and_resume_survives_app_restart(self):
        self.app.action("learning_mode")
        self.assertTrue(self.app.request.learning)
        self.assertEqual(self.app.learning_stats["missions"],0)
        self.assertIsNotNone(self.app.playback.episode.learning_id)
        self.app.update(20)  # Pausada: no avanzar ni entrenar.
        self.assertEqual(self.app.playback.index,0)
        self.finish()
        self.assertEqual(self.app.learning_stats["missions"],1)
        self.assertGreater(self.app.learning_stats["updates"],0)
        self.app.action("reset");self.finish()
        self.assertEqual(self.app.learning_stats["missions"],1)
        self.app.close()
        self.app=self.make_app()
        self.assertFalse(self.app.request.learning)
        self.assertEqual(self.app.playback.episode.checkpoint_sha256,self.original_hash)
        self.app.action("learning_mode")
        self.assertEqual(self.app.learning_stats["missions"],1)
        self.finish()
        self.assertEqual(self.app.learning_stats["missions"],2)
        self.assertEqual(digest(self.model),self.original_hash)

    def test_history_replay_and_comparison_do_not_add_training(self):
        self.app.action("learning_mode");self.finish()
        episode=self.app.playback.episode
        session=LearningSession.for_project(self.root,self.model,episode.scenario)
        checksum=session.snapshot().metadata["model_sha256"]
        self.app._start_replay(episode,"dqn",str(self.model),0)
        self.finish()
        self.assertEqual(session.snapshot().metadata["missions"],1)
        self.assertEqual(session.snapshot().metadata["model_sha256"],checksum)
        self.app.action("compare")
        deadline=time.monotonic()+30
        while self.app.comparison.futures and time.monotonic()<deadline:
            self.app.update(0);time.sleep(.01)
        self.assertFalse(self.app.comparison.futures)
        self.assertTrue(all(row.episode is None or row.episode.learning_id is None
                            for row in self.app.comparison.rows.values()))
        self.assertEqual(session.snapshot().metadata["missions"],1)
        self.assertEqual(digest(self.model),self.original_hash)

    def test_configuration_changes_wait_for_save_and_close_is_idempotent(self):
        future=Future();future.set_running_or_notify_cancel()
        self.app.learning_future=future
        scenario,strategy=self.app.scenario_index,self.app.strategy_index
        for action in ("scenario","strategy","models","edit","prepare","load_file","learning_mode","compare"):
            self.app.action(action)
        self.assertEqual(self.app.scenario_index,scenario)
        self.assertEqual(self.app.strategy_index,strategy)
        self.assertFalse(self.app.learning_enabled)
        future.set_result({"missions":1,"buffer_size":8,"updates":2})
        self.app.update(0)
        self.assertIsNone(self.app.learning_future)
        self.app.close();self.app.close();self.app.update(1)


if __name__=="__main__":unittest.main()
