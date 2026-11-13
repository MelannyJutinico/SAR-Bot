"""El reloj visual no modifica el motor ni sus resultados."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.ui.playback import Playback, prepare_episode


class PlaybackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.episode = prepare_episode(ROOT / "scenarios/demo.json", "shortest")

    def test_prepared_episode_contains_real_global_steps(self):
        self.assertEqual(len(self.episode.states), len(self.episode.actions) + 1)
        self.assertEqual([s.steps for s in self.episode.states], list(range(11)))
        self.assertEqual(self.episode.states[-1].outcome, "success")
        self.assertEqual(sum(r.damage for r in self.episode.states[-1].robots), 18)

    def test_pause_and_manual_step(self):
        playback = Playback(self.episode)
        playback.tick(50)
        self.assertEqual(playback.index, 0)
        playback.toggle()
        playback.tick(1 / 3)
        self.assertEqual(playback.index, 1)
        playback.toggle()
        playback.tick(50)
        self.assertEqual(playback.index, 1)
        playback.step()
        self.assertEqual(playback.index, 2)
        self.assertFalse(playback.playing)

    def test_playback_speed_does_not_change_damage_or_mission(self):
        results = []
        for speed in (1, 3, 12):
            playback = Playback(self.episode, speed)
            playback.toggle()
            playback.tick(100)
            self.assertTrue(playback.finished)
            self.assertFalse(playback.playing)
            results.append(playback.state)
        self.assertEqual(results, [self.episode.states[-1]] * 3)

    def test_reset_and_replay_restore_integrity_and_cargo(self):
        playback = Playback(self.episode)
        playback.toggle()
        playback.tick(100)
        playback.step()
        self.assertTrue(playback.finished)
        playback.toggle()
        self.assertEqual(playback.state, self.episode.states[0])
        self.assertTrue(playback.playing)
        playback.reset()
        self.assertFalse(playback.playing)
        self.assertEqual(playback.state.robots[0].integrity, 100)

    def test_random_restarts_use_same_seed(self):
        first = prepare_episode(ROOT / "scenarios/demo.json", "random", seed=3)
        second = prepare_episode(ROOT / "scenarios/demo.json", "random", seed=3)
        self.assertEqual(first, second)

    def test_invalid_speed_or_elapsed_time(self):
        playback = Playback(self.episode)
        for speed in (0, 13, 1.5, True):
            with self.assertRaises(ValueError):
                playback.set_speed(speed)
        for elapsed in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                playback.tick(elapsed)


if __name__ == "__main__":
    unittest.main()
