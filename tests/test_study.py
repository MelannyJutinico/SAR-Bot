"""SARB-031: conjunto de desarrollo generado y tablas de escala y dificultad.

Solo se usan entrenamiento, validación y desarrollo: la prueba no se abre aquí.
"""

from collections import Counter
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.core import Scenario
from sar_bot.core.generation import classify_difficulty
from sar_bot.development import (
    DEVELOPMENT_PURPOSE,
    build_development_set,
    verify_development_set,
    write_development_set,
)
from sar_bot.experiment import cases_from_development_set, summarize, read_results
from sar_bot.report import _dec
from sar_bot.study import build_study, case_features, check_study, load_dataset

TEMPLATE = "scenarios/v2/building_10x10.json"
VALIDATION = "results/sarb020/v2_12x12_validation_referencias.csv"
PILOT = "results/sarb020/v2_10x10_piloto_desarrollo.csv"


def small_set(root, **overrides):
    options = dict(template_path=TEMPLATE, root=root, set_id="prueba_10x10", building="building10",
                   seed=77, requested=3, max_attempts=500,
                   scenario_dir="scenarios/development/prueba", created_on="2026-11-18")
    options.update(overrides)
    return build_development_set(**options)


class DevelopmentSetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "scenarios/v2").mkdir(parents=True)
        shutil.copy(ROOT / TEMPLATE, self.root / TEMPLATE)

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        record, scenarios = small_set(self.root)
        return write_development_set(record, scenarios, "configs/development/prueba.json",
                                     self.root)

    def test_written_set_verifies_and_loads_as_development(self):
        path = self.write()
        self.assertEqual(verify_development_set(path, self.root), [])
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["purpose"], DEVELOPMENT_PURPOSE)
        self.assertEqual([e["difficulty"] for e in record["entries"]],
                         ["easy", "intermediate", "demanding"])
        template = Scenario.load(self.root / TEMPLATE)
        self.assertNotIn(template.scenario_id, {e["scenario_id"] for e in record["entries"]})
        cases = cases_from_development_set(path, self.root)
        self.assertEqual({c.partition for c in cases}, {"development"})
        self.assertEqual([c.difficulty for c in cases], ["easy", "intermediate", "demanding"])
        self.assertEqual({(c.manifest_id, c.building, c.generation_seed) for c in cases},
                         {("prueba_10x10", "building10", 77)})
        for case in cases:
            self.assertEqual(classify_difficulty(case.scenario, case.scenario.victims).value,
                             case.difficulty)

    def test_generation_is_reproducible(self):
        first, _ = small_set(self.root)
        second, _ = small_set(self.root)
        self.assertEqual(first, second)
        other, _ = small_set(self.root, seed=78)
        self.assertNotEqual([e["scenario_id"] for e in first["entries"]],
                            [e["scenario_id"] for e in other["entries"]])

    def test_never_overwrites(self):
        self.write()
        record, scenarios = small_set(self.root)
        with self.assertRaises(FileExistsError):
            write_development_set(record, scenarios, "configs/development/prueba.json", self.root)

    def test_detects_tampering(self):
        path = self.write()
        record = json.loads(path.read_text(encoding="utf-8"))
        scenario_path = self.root / record["entries"][0]["path"]
        scenario_path.write_text(scenario_path.read_text(encoding="utf-8").replace(
            '"max_steps"', '"max_steps" ', 1), encoding="utf-8")
        problems = verify_development_set(path, self.root)
        self.assertTrue(any("hash distinto" in p for p in problems), problems)
        with self.assertRaisesRegex(ValueError, "no está íntegro"):
            cases_from_development_set(path, self.root)
        record["notes"].append("editado a mano")
        path.write_text(json.dumps(record), encoding="utf-8")
        self.assertTrue(any("registro cambió" in p for p in verify_development_set(path, self.root)))


class FeatureTests(unittest.TestCase):
    def test_features_of_the_10x10_template(self):
        scenario = Scenario.load(ROOT / TEMPLATE)
        features = case_features(scenario)
        # Personas en (8,1), (1,8) y (8,8) con base en (0,0); escala 10 + 10 − 2 = 18.
        self.assertAlmostEqual(features.distance, (9 + 9 + 16) / (3 * 18))
        self.assertAlmostEqual(features.spread, (14 + 7 + 7) / (3 * 18))
        self.assertEqual(features.difficulty,
                         classify_difficulty(scenario, scenario.victims).value)

    def test_two_person_scenarios_have_no_family(self):
        features = case_features(Scenario.load(ROOT / "scenarios/pasillo_compartido.json"))
        self.assertEqual(features.difficulty, "")
        self.assertGreater(features.spread, 0)


class StudyTablesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = build_study(ROOT, [VALIDATION, PILOT], output_dir="outputs/estudio")
        cls.text = cls.files["tablas.md"].decode("utf-8")

    def test_scale_rows_match_the_shared_summary(self):
        for s in summarize(read_results(ROOT / VALIDATION)):
            if s["strategy"] == "random":
                continue
            with self.subTest(strategy=s["strategy"]):
                self.assertIn(f"| {s['successes']}/{s['episodes']} | {s['rescued']}/{s['victims']}"
                              f" | {_dec(s['mean_steps_success'])} | "
                              f"{_dec(s['mean_damage_success'])} |", self.text)

    def test_csv_family_must_match_the_generator(self):
        dataset = load_dataset(VALIDATION, ROOT, replay=False)
        for row in dataset.rows:
            self.assertEqual(row["difficulty"], dataset.feature(row).difficulty)

    def test_regeneration_and_check(self):
        self.assertEqual(build_study(ROOT, [PILOT, VALIDATION], output_dir="outputs/estudio"),
                         self.files)
        with tempfile.TemporaryDirectory() as folder:
            for name, data in self.files.items():
                (Path(folder) / name).write_bytes(data)
            self.assertEqual(check_study(folder, ROOT), [])
            tables = Path(folder) / "tablas.md"
            tables.write_text(tables.read_text(encoding="utf-8").replace("20/20", "19/20"),
                              encoding="utf-8")
            self.assertTrue(any("tablas.md" in p for p in check_study(folder, ROOT)))

    def test_no_percentages_and_profiles_kept_apart(self):
        self.assertNotIn("%", self.text)
        sources = json.loads(self.files["fuentes.json"])
        self.assertEqual(len(sources["results"]), 2)
        self.assertIn("10 × 10 · desarrollo · escenarios fijos", self.text)
        self.assertIn("12 × 12 · validación · v2_12x12_v1", self.text)
        counts = Counter(line.split(" | ")[0] for line in self.text.splitlines()
                         if line.startswith("| 12 × 12 · validación"))
        self.assertTrue(counts)



class CommittedStudyEvidenceTests(unittest.TestCase):
    RECORD = ROOT / "configs/development/v2_10x10_dev.json"

    def test_development_set_is_intact_and_balanced(self):
        self.assertEqual(verify_development_set(self.RECORD, ROOT), [])
        record = json.loads(self.RECORD.read_text(encoding="utf-8"))
        self.assertEqual(record["purpose"], DEVELOPMENT_PURPOSE)
        self.assertEqual(Counter(e["difficulty"] for e in record["entries"]),
                         {"easy": 10, "intermediate": 10, "demanding": 10})
        partitions = json.loads((ROOT / "configs/partitions/v2_12x12.json").read_text(
            encoding="utf-8"))
        frozen = {e["scenario_id"] for e in partitions["entries"]}
        self.assertFalse(frozen & {e["scenario_id"] for e in record["entries"]})

    def test_study_and_figures_match_their_sources(self):
        from sar_bot.report import check_report

        self.assertEqual(check_study(ROOT / "results/sarb031/estudio", ROOT), [])
        for folder in ("figuras_10x10_desarrollo", "figuras_12x12_entrenamiento"):
            with self.subTest(folder=folder):
                self.assertEqual(check_report(ROOT / "results/sarb031" / folder, ROOT), [])

    def test_study_never_reads_the_test_partition(self):
        sources = json.loads((ROOT / "results/sarb031/estudio/fuentes.json").read_text(
            encoding="utf-8"))
        for source in sources["results"]:
            with self.subTest(csv=source["path"]):
                rows = read_results(ROOT / source["path"])
                self.assertNotIn("test", {row["partition"] for row in rows})
                profiles = {(row["width"], row["height"], row["victims_total"]) for row in rows}
                self.assertEqual(len(profiles), 1)

    def test_dqn_rows_use_models_of_their_own_profile(self):
        expected = {"sensors_dqn": ("6", "6", "2"), "v2_pilot": ("10", "10", "3")}
        for name in ("v2_6x6_desarrollo.csv", "v2_10x10_desarrollo.csv"):
            for row in read_results(ROOT / "results/sarb031" / name):
                if row["strategy"] == "dqn":
                    self.assertEqual((row["width"], row["height"], row["victims_total"]),
                                     expected[row["model_label"]])


if __name__ == "__main__":
    unittest.main()
