"""Currículo real V2: selección, separación física y entrenamiento guardado."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.training import resolve_training_config
from sar_bot.core import Scenario


class TrainingPartitionTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "configs/dqn_v2_12x12.json").read_text(encoding="utf-8"))
        self.manifest = json.loads((ROOT / self.config["partition_manifest"]).read_text(encoding="utf-8"))

    def test_curriculum_uses_training_only_and_all_twenty_validation_cases(self):
        config, provenance = resolve_training_config(self.config, ROOT)
        self.assertEqual([len(s["scenarios"]) for s in config["stages"]], [8, 20, 60])
        for stage in config["stages"]:
            self.assertTrue(set(stage["scenarios"]) <= set(self.manifest["training"]))
        self.assertEqual(config["evaluation_scenarios"], self.manifest["validation"])
        self.assertFalse(provenance["test_evaluated"])
        self.assertNotIn("scenarios", self.config["stages"][0])

    def test_copied_validation_case_cannot_be_used_to_train(self):
        temporary_root = ROOT / "tmp/tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as directory:
            alias = Path(directory) / "renamed_training.json"
            alias.write_bytes((ROOT / self.manifest["validation"][0]).read_bytes())
            self.config["stages"][0].pop("training_filter")
            self.config["stages"][0]["scenarios"] = [str(alias)]
            with self.assertRaisesRegex(ValueError, "ajenos a entrenamiento"):
                resolve_training_config(self.config, ROOT)

    def test_rejects_test_selection_empty_filter_and_invalid_pilot(self):
        leaked = deepcopy(self.config)
        leaked["evaluation_scenarios"] = self.manifest["test"][:1]
        with self.assertRaisesRegex(ValueError, "validación"):
            resolve_training_config(leaked, ROOT)
        for steps in (0, -1, True):
            with self.assertRaises(ValueError):
                resolve_training_config(self.config, ROOT, steps)
        bad = deepcopy(self.config)
        bad["stages"][0]["training_filter"]["difficulties"] = []
        with self.assertRaises(ValueError):
            resolve_training_config(bad, ROOT)

    def test_pilot_records_effective_budget_and_legacy_still_works(self):
        config, _ = resolve_training_config(self.config, ROOT, 12)
        self.assertEqual([s["steps"] for s in config["stages"]], [12, 12, 12])
        legacy = json.loads((ROOT / "configs/dqn_v2_pilot.json").read_text(encoding="utf-8"))
        expanded, partition = resolve_training_config(legacy, ROOT)
        self.assertEqual(expanded, legacy)
        self.assertIsNone(partition)

    def test_distances_shared_by_geometry_and_observations_follow_changed_positions(self):
        from sar_bot.env import RescueEnv
        first = Scenario.load(ROOT / self.manifest["training"][0])
        second = first.with_victims(tuple(reversed(first.victims)))
        with patch.object(RescueEnv, "_compute_distances", wraps=RescueEnv._compute_distances) as compute:
            env = RescueEnv([first, second], observation_mode="sensors")
            self.assertEqual(compute.call_count, 1)
        self.assertIs(env._distances[0], env._distances[1])
        before, _ = env.reset(seed=17, options={"scenario_index": 0})
        after, _ = env.reset(seed=17, options={"scenario_index": 1})
        self.assertFalse((before == after).all())
        selected = [env.reset(seed=23)[1]["configuration_id"] for _ in range(2)]
        self.assertEqual(selected[0], selected[1])

    def test_cli_trains_saves_reloads_with_validation_metadata(self):
        temporary_root = ROOT / "tmp/tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as directory:
            directory = Path(directory)
            config = deepcopy(self.config)
            config["stages"] = config["stages"][:1]
            config["evaluation_scenarios"] = self.manifest["validation"][:2]
            config["dqn"].update(learning_starts=4, batch_size=8,
                                 buffer_size=100, policy_kwargs={"net_arch": [16, 16]})
            path = directory / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            run = directory / "run"
            result = subprocess.run([sys.executable, str(ROOT / "scripts/train.py"),
                                     "--config", str(path), "--run-dir", str(run),
                                     "--pilot-steps", "16", "--seed", "7"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            metadata = json.loads((run / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["evaluation_overlap_with_training"], [])
            self.assertEqual(metadata["partition_manifest"]["selection_split"], "validation")
            self.assertEqual(metadata["config"]["seed"], 7)
            self.assertEqual(metadata["observation_profile"]["observation_size"], 390)
            summary = json.loads((run / "training_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["training_steps"], 16)
            self.assertFalse(summary["test_evaluated"])
            self.assertTrue((run / "final_model.zip").is_file())
            from stable_baselines3 import DQN
            model = DQN.load(run / "final_model.zip", device="cpu")
            self.assertGreater(model._n_updates, 0)
            self.assertEqual(model.sar_bot_profile["width"], 12)


if __name__ == "__main__":
    unittest.main()
