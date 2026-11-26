"""SARB-021: la prueba final solo se abre con modelos congelados que cumplen el protocolo.

Los modelos son archivos falsos con metadatos: la comprobación no carga pesos
ni ejecuta misiones, y ningún caso de prueba se evalúa aquí.
"""

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.final_check import check_final_models

MANIFEST = ROOT / "configs/partitions/v2_12x12.json"
PARTITIONS = json.loads(MANIFEST.read_text(encoding="utf-8"))


class FinalCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def model(self, name, seed, *, training=None, selection=None, profile=(12, 12, 3),
              content=None, extra=None):
        folder = self.folder / name
        folder.mkdir()
        training = PARTITIONS["training"] if training is None else training
        selection = PARTITIONS["validation"] if selection is None else selection
        hashes = {path: sha256((ROOT / path).read_bytes()).hexdigest()
                  for path in sorted(set(training) | set(selection))}
        metadata = {
            "config": {"seed": seed,
                       "stages": [{"name": "variable", "steps": 1000, "scenarios": training}],
                       "evaluation_scenarios": selection},
            "observation_profile": {"width": profile[0], "height": profile[1],
                                    "victims": profile[2]},
            "scenario_hashes": hashes,
        }
        metadata.update(extra or {})
        (folder / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        (folder / "model.zip").write_bytes(content or f"pesos-{name}".encode())
        return folder / "model.zip"

    def three(self):
        if not hasattr(self, "_three"):
            self._three = [self.model(f"semilla{seed}", seed) for seed in (0, 1, 2)]
        return list(self._three)

    def check(self, models):
        return check_final_models(MANIFEST, models, ROOT)

    def test_protocol_compliant_models_pass(self):
        self.assertEqual(self.check(self.three()), [])

    def test_requires_three_distinct_seeds_and_models(self):
        models = self.three()
        self.assertTrue(any("al menos 3" in p for p in self.check(models[:2])))
        repeated = self.model("repetida", 1)
        self.assertTrue(any("repite la semilla 1" in p for p in self.check(models + [repeated])))
        copy = self.model("copia", 7, content=b"pesos-semilla0")
        self.assertTrue(any("mismo archivo" in p for p in self.check(models + [copy])))

    def test_rejects_training_on_reserved_cases(self):
        leaked = self.model("fuga", 3, training=PARTITIONS["training"] + PARTITIONS["test"][:1])
        problems = self.check(self.three()[:2] + [leaked])
        self.assertTrue(any("entrenó con" in p and "prueba" in p for p in problems), problems)
        validation = self.model("fuga_validacion", 4,
                                training=PARTITIONS["training"] + PARTITIONS["validation"][:1])
        self.assertTrue(any("entrenó con" in p for p in self.check(self.three()[:2] + [validation])))

    def test_checkpoint_must_be_chosen_on_validation_only(self):
        on_test = self.model("elige_prueba", 3, selection=PARTITIONS["test"][:2])
        problems = self.check(self.three()[:2] + [on_test])
        self.assertTrue(any("que es de prueba" in p for p in problems), problems)
        on_training = self.model("elige_entrenamiento", 4, selection=PARTITIONS["training"][:2])
        problems = self.check(self.three()[:2] + [on_training])
        self.assertTrue(any("no es de validación" in p for p in problems), problems)

    def test_rejects_other_profiles_and_changed_scenarios(self):
        small = self.model("diez", 3, profile=(10, 10, 3))
        self.assertTrue(any("perfil 10×10" in p for p in self.check(self.three()[:2] + [small])))
        stale = self.model("antiguo", 4)
        metadata = json.loads((stale.parent / "metadata.json").read_text(encoding="utf-8"))
        first = PARTITIONS["training"][0]
        metadata["scenario_hashes"][first] = "0" * 64
        (stale.parent / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        problems = self.check(self.three()[:2] + [stale])
        self.assertTrue(any("cambió después del entrenamiento" in p for p in problems), problems)

    def test_test_partition_cannot_be_opened_twice(self):
        models = self.three()
        (models[0].parent / "test.csv").write_text("ya evaluado\n", encoding="utf-8")
        self.assertTrue(any("abrirse dos veces" in p for p in self.check(models)))

    def test_current_development_models_are_rejected(self):
        problems = self.check([ROOT / "artifacts/v2_pilot/model.zip",
                               ROOT / "artifacts/sensors_dqn/model.zip"])
        self.assertTrue(any("al menos 3" in p for p in problems))
        self.assertTrue(any("v2_pilot: perfil 10×10" in p for p in problems))
        self.assertTrue(any("sensors_dqn: perfil" in p for p in problems))

    def test_evaluator_refuses_before_reading_test_cases(self):
        output = self.folder / "prueba.csv"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/evaluate_experiment.py"), "--manifest",
             str(MANIFEST), "--split", "test", "--final", "--model",
             str(ROOT / "artifacts/v2_pilot/model.zip"), "--output", str(output)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={"PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8",
                 "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")})
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("No se abre la prueba final", result.stdout)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
