"""SARB-020: mismas entradas para todas las estrategias y métricas fieles a la traza."""

import csv
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.env import RewardConfig
from sar_bot.experiment import (
    COLUMNS,
    NONDETERMINISTIC_COLUMNS,
    cases_from_manifest,
    cases_from_paths,
    evaluate_cases,
    load_model,
    metrics_from_trace,
    replay_actions,
    run_episode,
    summarize,
    verify_results,
    write_results,
)
from sar_bot.learning import evaluate_model

MANIFEST = ROOT / "configs/partitions/v2_12x12.json"


def stable(row):
    return {k: v for k, v in row.items() if k not in NONDETERMINISTIC_COLUMNS}


class UnifiedEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.building = cases_from_paths(["scenarios/v2/building_10x10.json"], ROOT)
        cls.rows, cls.traces = evaluate_cases(
            cls.building, strategies=("shortest", "thermal", "random"), random_seeds=(0, 1, 2))
        cls.sensors = load_model(ROOT / "artifacts/sensors_dqn/model.zip")

    def test_documented_reference_results_are_reproduced(self):
        by_strategy = {row["strategy"]: row for row in self.rows if row["strategy"] != "random"}
        self.assertEqual((by_strategy["thermal"]["rescued"], by_strategy["thermal"]["steps"],
                          by_strategy["thermal"]["damage_total"]), (3, 62, 64))
        self.assertEqual((by_strategy["shortest"]["rescued"], by_strategy["shortest"]["steps"],
                          by_strategy["shortest"]["damage_total"]), (3, 58, 107))

    def test_every_strategy_receives_the_same_frozen_case(self):
        identity = {(r["scenario_id"], r["configuration_id"], r["scenario_sha256"],
                     r["max_steps"], r["victims_total"]) for r in self.rows}
        self.assertEqual(len(identity), 1)
        self.assertEqual(len({r["episode_id"] for r in self.rows}), len(self.rows))

    def test_seed_kinds_are_kept_apart(self):
        counts = {s: sum(1 for r in self.rows if r["strategy"] == s)
                  for s in ("shortest", "thermal", "random")}
        self.assertEqual(counts, {"shortest": 1, "thermal": 1, "random": 3})
        for row in self.rows:
            if row["strategy"] == "random":
                self.assertIn(row["random_seed"], (0, 1, 2))
            else:
                self.assertIsNone(row["random_seed"])
            self.assertIsNone(row["training_seed"])
            self.assertEqual(row["model_sha256"], "")

    def test_metrics_match_a_fresh_engine_replay(self):
        scenario = self.building[0].scenario
        for row, trace in zip(self.rows, self.traces):
            with self.subTest(strategy=row["strategy"], seed=row["random_seed"]):
                states = replay_actions(scenario, trace["actions"])
                replayed = metrics_from_trace(scenario, states, trace["actions"])
                for column, value in replayed.items():
                    self.assertEqual(row[column], value, column)
                deliveries = row["deliveries_robot_1"] + row["deliveries_robot_2"]
                self.assertEqual(deliveries, row["rescued"])

    def test_no_state_leaks_between_episodes(self):
        warmup = cases_from_paths(["scenarios/v2/warmup_10x10.json"], ROOT)
        mixed, _ = evaluate_cases(warmup + self.building, strategies=("thermal", "random"),
                                  random_seeds=(3,))
        alone, _ = evaluate_cases(self.building, strategies=("thermal", "random"),
                                  random_seeds=(3,))
        tail = [r for r in mixed if r["configuration_id"] == self.building[0].scenario.configuration_id]
        self.assertEqual([stable(r) for r in tail], [stable(r) for r in alone])
        again, _ = evaluate_cases(self.building, strategies=("thermal", "random"), random_seeds=(3,))
        self.assertEqual([stable(r) for r in again], [stable(r) for r in alone])

    def test_dqn_row_matches_existing_evaluator_and_records_model(self):
        corridor = cases_from_paths(["scenarios/pasillo_compartido.json"], ROOT)
        rewards = RewardConfig(**self.sensors.reward_config)
        row, actions = run_episode(corridor[0], "dqn", model=self.sensors, rewards=rewards)
        self.assertEqual((row["outcome"], row["rescued"], row["steps"], row["damage_total"]),
                         ("success", 2, 22, 0))
        legacy = evaluate_model(self.sensors.model, [corridor[0].scenario], rewards)[0]
        self.assertEqual((row["steps"], row["damage_total"], row["return"]),
                         (legacy["steps"], legacy["damage_total"], round(legacy["return"], 6)))
        self.assertEqual(len(row["model_sha256"]), 64)
        self.assertEqual(row["training_seed"], 0)
        self.assertEqual(len(actions), 22)

    def test_profiles_and_incompatible_models_are_rejected(self):
        corridor = cases_from_paths(["scenarios/pasillo_compartido.json"], ROOT)
        with self.assertRaisesRegex(ValueError, "perfiles"):
            evaluate_cases(corridor + self.building, strategies=("thermal",))
        with self.assertRaises(ValueError):
            evaluate_cases(self.building, models=[self.sensors], strategies=("dqn",))

    def test_summary_compares_damage_only_between_successes(self):
        summary = {s["strategy"]: s for s in summarize(self.rows)}
        self.assertEqual(summary["random"]["episodes"], 3)
        self.assertEqual(summary["thermal"]["mean_damage_success"], 64)
        if summary["random"]["successes"] == 0:
            self.assertIsNone(summary["random"]["mean_damage_success"])


class ResultFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cases = cases_from_manifest(MANIFEST, "validation", ROOT)[:2]
        cls.rows, cls.traces = evaluate_cases(cases, strategies=("shortest", "thermal", "random"),
                                              random_seeds=(0,))
        cls.output = Path(cls.temp.name) / "eval.csv"
        cls.metadata = write_results(cls.rows, cls.traces, cls.output, {"partition": "validation"})

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def copy(self):
        folder = Path(tempfile.mkdtemp(dir=self.temp.name))
        for suffix in (".csv", ".traces.jsonl", ".metadata.json"):
            shutil.copy(self.output.with_suffix(suffix), folder / ("eval" + suffix))
        return folder / "eval.csv"

    def test_written_csv_has_fixed_columns_and_replays(self):
        with self.output.open(encoding="utf-8", newline="") as stream:
            header = next(csv.reader(stream))
        self.assertEqual(tuple(header), COLUMNS)
        self.assertEqual(verify_results(self.output, ROOT), [])
        self.assertEqual(self.metadata["episodes"], 6)
        self.assertEqual(self.metadata["configurations"], 2)
        with self.output.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual({r["manifest_id"] for r in rows}, {"v2_12x12_v1"})
        self.assertTrue(all(r["generation_seed"] for r in rows))

    def test_detects_metric_not_backed_by_trace(self):
        path = self.copy()
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        rows[0]["damage_total"] = str(int(rows[0]["damage_total"]) + 1)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        problems = verify_results(path, ROOT)
        self.assertTrue(any("CSV cambió" in p for p in problems), problems)
        self.assertTrue(any("damage_total" in p for p in problems), problems)

    def test_detects_swapped_trace(self):
        path = self.copy()
        traces = path.with_suffix(".traces.jsonl")
        records = [json.loads(line) for line in traces.read_text(encoding="utf-8").splitlines()]
        # Dos episodios con acciones distintas (la ruta corta y la térmica pueden coincidir).
        j = next(i for i, r in enumerate(records) if r["actions"] != records[0]["actions"])
        records[0]["actions"], records[j]["actions"] = records[j]["actions"], records[0]["actions"]
        traces.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        problems = verify_results(path, ROOT)
        self.assertTrue(any("hash de acciones" in p for p in problems), problems)

    def test_test_partition_requires_explicit_final_evaluation(self):
        with self.assertRaises(PermissionError):
            cases_from_manifest(MANIFEST, "test", ROOT)
        with self.assertRaises(ValueError):
            cases_from_paths(["scenarios/demo.json"], ROOT, partition="test")

    def test_column_dictionary_documents_every_column(self):
        text = (ROOT / "docs/METRICAS.md").read_text(encoding="utf-8")
        documented = set(re.findall(r"^\| `([a-z0-9_]+)` \|", text, flags=re.MULTILINE))
        self.assertEqual(documented, set(COLUMNS))


if __name__ == "__main__":
    unittest.main()
