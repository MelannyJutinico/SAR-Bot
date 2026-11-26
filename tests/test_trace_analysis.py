"""SARB-023: las descripciones salen de trazas reproducidas y coinciden con el CSV."""

import csv
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.core import Scenario
from sar_bot.experiment import read_results
from sar_bot.trace_analysis import (
    build_trace_report,
    cell,
    check_trace_report,
    episode_story,
)

CASES = "configs/analysis/sarb023_casos.json"
TRAINING = ROOT / "results/sarb031/v2_12x12_training_referencias.csv"
DEVELOPMENT = ROOT / "results/sarb031/v2_10x10_desarrollo.csv"


def row_and_actions(csv_path, scenario, strategy, model_label=""):
    row = next(r for r in read_results(csv_path) if r["scenario_path"] == scenario
               and r["strategy"] == strategy and r["model_label"] == model_label)
    for line in csv_path.with_suffix(".traces.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record["episode_id"] == row["episode_id"]:
            return row, record["actions"]
    raise AssertionError("sin traza")


class EpisodeStoryTests(unittest.TestCase):
    def test_cell_names_follow_the_interface(self):
        self.assertEqual((cell((0, 0)), cell((4, 6)), cell((11, 11))), ("A1", "E7", "L12"))

    def test_per_robot_totals_add_up_to_the_csv_row(self):
        scenario_path = "scenarios/partitions/v2_12x12/training/detour_training_14_intermediate.json"
        scenario = Scenario.load(ROOT / scenario_path)
        for strategy in ("shortest", "thermal"):
            with self.subTest(strategy=strategy):
                row, actions = row_and_actions(TRAINING, scenario_path, strategy)
                story = episode_story(scenario, actions)
                robots = story["robots"]
                self.assertEqual(sum(r["damage"] for r in robots), int(row["damage_total"]))
                self.assertEqual(sum(r["blocked"] for r in robots), int(row["blocked_moves"]))
                self.assertEqual(sum(r["waits"] for r in robots), int(row["wait_actions"]))
                self.assertEqual([r["deliveries"] for r in robots],
                                 [int(row["deliveries_robot_1"]), int(row["deliveries_robot_2"])])
                self.assertEqual(len(story["trips"]), int(row["rescued"]))
                for trip in story["trips"]:
                    self.assertLess(trip["pickup"], trip["delivery"])

    def test_destruction_and_partial_rescue_are_reported(self):
        scenario_path = "scenarios/partitions/v2_12x12/training/detour_training_14_intermediate.json"
        row, actions = row_and_actions(TRAINING, scenario_path, "shortest")
        story = episode_story(Scenario.load(ROOT / scenario_path), actions)
        texts = [text for _, text in story["events"]]
        self.assertTrue(any("queda destruido" in t and "cargando a la persona" in t for t in texts))
        self.assertEqual(story["outcome"], "destroyed")
        self.assertEqual([r["integrity"] for r in story["robots"]],
                         [int(row["integrity_robot_1"]), int(row["integrity_robot_2"])])

    def test_long_blocked_streaks_are_summarised(self):
        scenario_path = "scenarios/development/v2_10x10/building10_dev_16_easy.json"
        row, actions = row_and_actions(DEVELOPMENT, scenario_path, "dqn", "v2_pilot")
        story = episode_story(Scenario.load(ROOT / scenario_path), actions)
        texts = [text for _, text in story["events"]]
        self.assertEqual(sum(r["blocked"] for r in story["robots"]), int(row["blocked_moves"]))
        self.assertTrue(any("no logra moverse" in t for t in texts))
        self.assertTrue(texts[-1].startswith("Termina en el paso 240"))
        self.assertIn("sin recoger", texts[-1])


class TraceReportTests(unittest.TestCase):
    def test_committed_report_matches_its_sources(self):
        self.assertEqual(check_trace_report(ROOT / "results/sarb023", ROOT), [])

    def test_report_is_deterministic_and_detects_edits(self):
        files = build_trace_report(CASES, ROOT)
        self.assertEqual(build_trace_report(CASES, ROOT), files)
        with tempfile.TemporaryDirectory() as folder:
            for name, data in files.items():
                (Path(folder) / name).write_bytes(data)
            self.assertEqual(check_trace_report(folder, ROOT), [])
            report = Path(folder) / "trazas.md"
            report.write_text(report.read_text(encoding="utf-8").replace("daño 190", "daño 19"),
                              encoding="utf-8")
            self.assertTrue(any("trazas.md" in p for p in check_trace_report(folder, ROOT)))

    def test_cases_never_come_from_the_test_partition(self):
        config = json.loads((ROOT / CASES).read_text(encoding="utf-8"))
        for case in config["cases"]:
            rows = read_results(ROOT / case["results"])
            self.assertNotIn("test", {r["partition"] for r in rows})
            self.assertNotIn("/test/", case["scenario"])

    def test_refuses_a_trace_that_does_not_match_the_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            source = TRAINING
            for suffix in (".csv", ".metadata.json", ".traces.jsonl"):
                shutil.copy(source.with_suffix(suffix), Path(folder) / ("eval" + suffix))
            csv_path = Path(folder) / "eval.csv"
            with csv_path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
                columns = list(rows[0])
            rows[0]["damage_total"] = str(int(rows[0]["damage_total"]) + 1)
            with csv_path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            config = {"cases": [{"key": "alterado", "role": "Alterado", "results": str(csv_path),
                                 "scenario": rows[0]["scenario_path"],
                                 "strategy": rows[0]["strategy"],
                                 "model_label": rows[0]["model_label"],
                                 "random_seed": rows[0]["random_seed"]}]}
            config_path = Path(folder) / "casos.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no está íntegro"):
                build_trace_report(config_path, ROOT)


if __name__ == "__main__":
    unittest.main()
