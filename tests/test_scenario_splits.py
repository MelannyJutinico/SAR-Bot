"""Separación de entradas y viabilidad de rescates; sin consultar DQN."""

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.agents import ShortestPathPolicy
from sar_bot.core import RescueSimulation, Scenario
from sar_bot.evaluation import evaluate_episode


class ScenarioSplitTests(unittest.TestCase):
    def test_partitions_have_distinct_files_and_scenarios(self):
        splits = json.loads((ROOT / "configs/scenario_splits.json").read_text(encoding="utf-8"))
        paths = [path for partition in splits.values() for path in partition]
        self.assertEqual(len(paths), len(set(paths)))
        scenarios = [Scenario.load(ROOT / path) for path in paths]
        self.assertEqual(len(scenarios), len({s.name for s in scenarios}))
        signatures = [(s.base, s.victims, s.walls, s.temperatures) for s in scenarios]
        self.assertEqual(len(signatures), len(set(signatures)))
        config = json.loads((ROOT / "configs/dqn_cooperation.json").read_text(encoding="utf-8"))
        used = {path for stage in config["stages"] for path in stage["scenarios"]}
        self.assertLessEqual(used, set(splits["training"]))
        self.assertFalse(used & set(splits["validation"] + splits["test"]))
        self.assertLessEqual(set(config["evaluation_scenarios"]), set(splits["training"]))
        sensors = json.loads((ROOT / "configs/dqn_sensors.json").read_text(encoding="utf-8"))
        sensor_inputs = {path for stage in sensors["stages"] for path in stage["scenarios"]}
        self.assertLessEqual(sensor_inputs | set(sensors["evaluation_scenarios"]), set(splits["training"]))

    def test_unseen_scenarios_are_physically_solvable(self):
        splits = json.loads((ROOT / "configs/scenario_splits.json").read_text(encoding="utf-8"))
        for path in splits["validation"] + splits["test"]:
            with self.subTest(path=path):
                sim = RescueSimulation(Scenario.load(ROOT / path))
                result = evaluate_episode(sim, ShortestPathPolicy(sim), "shortest")
                self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
