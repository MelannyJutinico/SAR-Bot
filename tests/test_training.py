"""Regresión de exploración al continuar un entrenamiento por etapas."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.training import StageExploration


class StageExplorationTests(unittest.TestCase):
    def test_later_stage_restarts_exploration_instead_of_using_elapsed_steps(self):
        schedule = StageExploration(42000, 40000, initial=0.6, final=0.05, fraction=0.8)
        total = 82000
        self.assertAlmostEqual(schedule(1 - 42000 / total), 0.6)
        self.assertAlmostEqual(schedule(1 - 58000 / total), 0.325)
        self.assertAlmostEqual(schedule(1 - 74000 / total), 0.05)
        self.assertAlmostEqual(schedule(0), 0.05)

    def test_first_stage_and_outside_local_bounds(self):
        schedule = StageExploration(0, 100, initial=1, final=0.1, fraction=0.5)
        self.assertEqual(schedule(1), 1)
        self.assertAlmostEqual(schedule(0.5), 0.1)
        self.assertAlmostEqual(schedule(-0.001), 0.1)

    def test_rejects_invalid_probability_or_duration(self):
        for kwargs in (dict(steps=0), dict(start_step=-1), dict(initial=2),
                       dict(final=0.9), dict(fraction=0), dict(fraction=float("nan"))):
            values = {"start_step": 0, "steps": 100, **kwargs}
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                StageExploration(**values)


if __name__ == "__main__":
    unittest.main()
