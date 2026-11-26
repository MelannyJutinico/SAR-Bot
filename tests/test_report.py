"""SARB-022: tablas y figuras generadas desde los CSV conservados, con denominadores.

Solo se usan la validación y escenarios de desarrollo: la partición de prueba no
se abre aquí.
"""

from collections import defaultdict
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.core import Scenario
from sar_bot.experiment import COLUMNS, read_results, summarize
from sar_bot.report import (
    OUTCOMES_FIGURE,
    SOURCES_FILE,
    SUCCESS_METRICS_FIGURE,
    TABLES_FILE,
    TRADEOFF_FIGURE,
    TRAINING_FIGURE,
    build_report,
    check_report,
    load_results,
    load_training_log,
    pairing,
    reference_pair,
    write_report,
)

VALIDATION = "results/sarb020/v2_12x12_validation_referencias.csv"
PILOT = "results/sarb020/v2_10x10_piloto_desarrollo.csv"
EVIDENCE = ("results/sarb022/validacion_12x12", "results/sarb022/piloto_10x10")
NS = "{http://www.w3.org/2000/svg}"


def parse(data: bytes):
    return ET.fromstring(data)


def marks(root, tag, cls):
    return [e for e in root.iter(NS + tag) if e.get("class") == cls]


def slug(summary_row):
    label = summary_row["model_label"]
    return f"{summary_row['strategy']}:{label}" if label else summary_row["strategy"]


def bar_length(path_d: str) -> float:
    """Longitud de una barra a partir de su trazo: tramo recto más el radio del extremo."""
    straight, radius = re.match(r"M[\d.]+,[\d.]+h([\d.]+)a([\d.]+)", path_d).groups()
    return float(straight) + float(radius)


class ValidationReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = build_report(ROOT, results=VALIDATION, output_dir=EVIDENCE[0])
        cls.episodes, cls.metadata = load_results(ROOT / VALIDATION, ROOT, replay=False)
        cls.rows = read_results(ROOT / VALIDATION)
        cls.tables = cls.files[TABLES_FILE].decode("utf-8")

    def test_outcome_bars_carry_the_csv_counts(self):
        root = parse(self.files[OUTCOMES_FIGURE])
        labels = {(e.get("data-group"), e.get("data-series"), e.get("data-metric")): e
                  for e in marks(root, "text", "bar-label")}
        bars = {(e.get("data-group"), e.get("data-series"), e.get("data-metric")): e
                for e in marks(root, "path", "bar")}
        expected = [("all", s) for s in summarize(self.rows)]
        expected += [(s["building"], s) for s in summarize(
            self.rows, keys=("building", "strategy", "model_label"))]
        self.assertEqual(len(labels), 2 * len(expected))
        for group, s in expected:
            for metric, k, n in (("success", s["successes"], s["episodes"]),
                                 ("rescued", s["rescued"], s["victims"])):
                with self.subTest(group=group, series=slug(s), metric=metric):
                    label = labels[(group, slug(s), metric)]
                    self.assertEqual(label.text, f"{k}/{n}")
                    self.assertEqual((int(label.get("data-k")), int(label.get("data-n"))), (k, n))
                    bar = bars.get((group, slug(s), metric))
                    if k == 0:
                        self.assertIsNone(bar)
                    else:
                        self.assertAlmostEqual(bar_length(bar.get("d")), 240 * k / n, places=1)

    def test_percent_signs_only_on_axes(self):
        for name, data in self.files.items():
            if not name.endswith(".svg"):
                self.assertNotIn("%", data.decode("utf-8"), name)
                continue
            for text in parse(data).iter(NS + "text"):
                if "%" in (text.text or ""):
                    self.assertIn(text.get("class"), ("tick", "axis-title"), (name, text.text))

    def test_steps_and_damage_come_only_from_successes(self):
        root = parse(self.files[SUCCESS_METRICS_FIGURE])
        for s in summarize(self.rows):
            for metric, mean in (("steps", s["mean_steps_success"]),
                                 ("damage", s["mean_damage_success"])):
                with self.subTest(series=slug(s), metric=metric):
                    selected = [e for e in marks(root, "circle", "dot")
                                if (e.get("data-group"), e.get("data-series"),
                                    e.get("data-metric")) == ("all", slug(s), metric)]
                    self.assertEqual(len(selected), s["successes"])
                    lines = [e for e in marks(root, "line", "mean")
                             if (e.get("data-group"), e.get("data-series"),
                                 e.get("data-metric")) == ("all", slug(s), metric)]
                    if s["successes"]:
                        self.assertEqual(len(lines), 1)
                        self.assertEqual(int(lines[0].get("data-n")), s["successes"])
                        self.assertAlmostEqual(float(lines[0].get("data-value")), mean, delta=0.05)
                    else:
                        self.assertEqual(lines, [])
        counts = {(e.get("data-group"), e.get("data-series")): e.text
                  for e in marks(root, "text", "count")}
        self.assertEqual(counts[("all", "random")], "0/100")

    def test_paired_comparison_uses_cases_solved_by_both(self):
        by_case = defaultdict(dict)
        for row in self.rows:
            if row["strategy"] in ("shortest", "thermal"):
                by_case[row["configuration_id"]][row["strategy"]] = row
        both = [c for c, d in by_case.items()
                if d["shortest"]["success"] == "True" and d["thermal"]["success"] == "True"]
        shortest, thermal = reference_pair(self.episodes)
        p = pairing(self.episodes, shortest, thermal)
        self.assertEqual(p.shared, 20)
        self.assertEqual(len(p.both), len(both))
        self.assertEqual(p.only_a + p.only_b + p.neither + len(p.both), p.shared)
        expected = sum(int(by_case[c]["thermal"]["damage_total"])
                       - int(by_case[c]["shortest"]["damage_total"]) for c in both) / len(both)
        self.assertAlmostEqual(p.difference("damage"), expected)
        root = parse(self.files[TRADEOFF_FIGURE])
        self.assertEqual(len(marks(root, "line", "pair")), len(both))
        successes = sum(row["success"] == "True" for row in self.rows)
        self.assertEqual(len(marks(root, "circle", "point")), successes)
        self.assertIn(f"| Ruta corta | Ruta térmica | 20 | {len(both)} | {p.only_a} | "
                      f"{p.only_b} | {p.neither} |", self.tables)

    def test_tables_match_the_summary_and_record_sources(self):
        for s in summarize(self.rows):
            with self.subTest(series=slug(s)):
                self.assertRegex(self.tables, re.escape(
                    f"| {s['episodes']} | {s['configurations']} | {s['successes']}/{s['episodes']}"
                    f" | {s['rescued']}/{s['victims']} | {s['destroyed']} | {s['time_limit']} |"))
        sources = json.loads(self.files[SOURCES_FILE])
        self.assertEqual(sources["results"]["sha256"], self.metadata["csv_sha256"])
        self.assertEqual(sources["results"]["traces_sha256"], self.metadata["traces_sha256"])
        self.assertTrue(sources["results"]["replayed"])
        self.assertEqual(set(sources["outputs"]), set(self.files) - {SOURCES_FILE})
        for name, digest in sources["outputs"].items():
            self.assertEqual(sha256(self.files[name]).hexdigest(), digest)
        self.assertIn(sources["command"], self.tables)
        self.assertIn("no es la evaluación final reservada", self.tables)
        self.assertNotIn(TRAINING_FIGURE, self.files)

    def test_regeneration_is_byte_identical(self):
        self.assertEqual(build_report(ROOT, results=VALIDATION, output_dir=EVIDENCE[0]),
                         self.files)

    def test_svg_files_are_well_formed_and_described(self):
        for name, data in self.files.items():
            if not name.endswith(".svg"):
                continue
            with self.subTest(figure=name):
                root = parse(data)
                width = float(root.get("width"))
                self.assertEqual(root.get("viewBox"), f"0 0 {root.get('width')} {root.get('height')}")
                self.assertTrue(root.find(NS + "title").text)
                self.assertTrue(root.find(NS + "desc").text)
                for text in root.iter(NS + "text"):
                    x = float(text.get("x"))
                    self.assertTrue(0 <= x <= width, (text.text, x))
                    if text.get("text-anchor") is None:
                        # Cota inferior del ancho real: el texto no debe salirse de la figura.
                        minimum = len(text.text) * float(text.get("font-size")) * 0.45
                        self.assertLessEqual(x + minimum, width, text.text)

    def test_tampered_csv_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            source = ROOT / VALIDATION
            for suffix in (".csv", ".metadata.json", ".traces.jsonl"):
                shutil.copy(source.with_suffix(suffix), Path(folder) / ("eval" + suffix))
            csv_path = Path(folder) / "eval.csv"
            with csv_path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            rows[0]["steps"] = str(int(rows[0]["steps"]) + 1)
            with csv_path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            for replay in (True, False):
                with self.assertRaisesRegex(ValueError, "no está íntegro"):
                    build_report(ROOT, results=csv_path, replay=replay)


class TrainingCurveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.log = load_training_log("artifacts/v2_pilot", ROOT)
        cls.records = [json.loads(line) for line in (ROOT / "artifacts/v2_pilot/evaluations.jsonl")
                       .read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_points_follow_the_evaluation_log(self):
        self.assertEqual(len(self.log.points), len(self.records))
        for point, record in zip(self.log.points, self.records):
            self.assertEqual(point.steps, record["steps"])
            self.assertEqual(point.rescued, sum(r["rescued"] for r in record["results"]))
        best = max(self.records, key=lambda r: tuple(r["score"]))
        self.assertEqual(self.log.selected_point.steps, best["steps"])
        packaged = json.loads((ROOT / "artifacts/v2_pilot/best_results.json").read_text(
            encoding="utf-8"))
        self.assertEqual(self.log.selected_point.rescued, sum(r["rescued"] for r in packaged))
        self.assertEqual(self.log.overlap_with_training, 2)
        self.assertEqual(self.log.seed, 0)

    def test_figure_marks_the_selected_checkpoint(self):
        files = build_report(ROOT, results=PILOT, training=["artifacts/v2_pilot"],
                             output_dir=EVIDENCE[1])
        root = parse(files[TRAINING_FIGURE])
        curve, = marks(root, "path", "curve")
        self.assertEqual(int(curve.get("data-points")), len(self.records))
        checkpoint, = marks(root, "circle", "checkpoint")
        self.assertEqual(int(checkpoint.get("data-steps")), self.log.selected_point.steps)
        texts = " ".join(t.text or "" for t in root.iter(NS + "text"))
        self.assertIn("2 también usados para entrenar", texts)

    def test_old_logs_without_victim_totals_use_the_scenarios(self):
        log = load_training_log("artifacts/initial_dqn", ROOT)
        metadata = json.loads((ROOT / "artifacts/initial_dqn/metadata.json").read_text(
            encoding="utf-8"))
        expected = sum(Scenario.load(ROOT / path).victim_count
                       for path in metadata["config"]["evaluation_scenarios"])
        self.assertEqual({p.victims for p in log.points}, {expected})

    def test_curves_must_belong_to_the_evaluated_models(self):
        with self.assertRaisesRegex(ValueError, "model.zip"):
            build_report(ROOT, results=PILOT, training=["artifacts/sensors_dqn"])
        with self.assertRaisesRegex(ValueError, "filas DQN"):
            build_report(ROOT, results=VALIDATION, training=["artifacts/v2_pilot"])


class CommittedEvidenceTests(unittest.TestCase):
    def test_committed_directories_match_their_sources(self):
        for folder in EVIDENCE:
            with self.subTest(folder=folder):
                self.assertEqual(check_report(ROOT / folder, ROOT), [])

    def test_check_detects_manual_edits(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "figuras"
            shutil.copytree(ROOT / EVIDENCE[0], copy)
            self.assertEqual(check_report(copy, ROOT), [])
            tables = copy / TABLES_FILE
            tables.write_text(tables.read_text(encoding="utf-8").replace("17/20", "18/20"),
                              encoding="utf-8")
            (copy / OUTCOMES_FIGURE).unlink()
            problems = check_report(copy, ROOT)
            self.assertTrue(any(TABLES_FILE in p for p in problems), problems)
            self.assertTrue(any(f"Falta {OUTCOMES_FIGURE}" in p for p in problems), problems)

    def test_write_report_keeps_lf_content(self):
        files = {"a.svg": b"<svg/>\n"}
        with tempfile.TemporaryDirectory() as folder:
            written = write_report(files, folder)
            self.assertEqual(written[0].read_bytes(), b"<svg/>\n")

    def test_cli_can_write_outside_the_repository(self):
        import os
        import subprocess

        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/report_figures.py"), "--results", VALIDATION,
                 "--skip-replay", "--output-dir", folder],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((Path(folder) / TABLES_FILE).is_file())
            self.assertEqual(check_report(folder, ROOT), [])


if __name__ == "__main__":
    unittest.main()
