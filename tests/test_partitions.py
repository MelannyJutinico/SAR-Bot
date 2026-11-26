"""SARB-009: particiones congeladas, separadas, reproducibles y verificables."""

import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.core import Scenario, generate_configurations
from sar_bot.partitions import (
    build_partitions,
    check_training_configs,
    content_sha256,
    file_sha256,
    verify_manifest,
    write_partitions,
)

MANIFEST = ROOT / "configs/partitions/v2_12x12.json"


class FrozenManifestTests(unittest.TestCase):
    """Comprueba el manifiesto publicado, no uno regenerado."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_published_manifest_is_intact_and_witnesses_replay(self):
        self.assertEqual(verify_manifest(MANIFEST, ROOT), [])

    def test_planned_sizes_and_minimum_test(self):
        sizes = {p: len(self.manifest[p]) for p in ("training", "validation", "test")}
        self.assertEqual(sizes, {"training": 60, "validation": 20, "test": 40})
        self.assertGreaterEqual(sizes["test"], 20)
        for building in ("hub", "detour"):
            with self.subTest(building=building):
                counts = {p: sum(1 for e in self.manifest["entries"]
                                 if (e["building"], e["partition"]) == (building, p))
                          for p in ("training", "validation", "test")}
                self.assertEqual(counts, {"training": 30, "validation": 10, "test": 20})

    def test_physical_signatures_do_not_cross_partitions(self):
        by_partition = {p: {e["scenario_id"] for e in self.manifest["entries"]
                            if e["partition"] == p} for p in ("training", "validation", "test")}
        self.assertFalse(by_partition["training"] & by_partition["validation"])
        self.assertFalse(by_partition["training"] & by_partition["test"])
        self.assertFalse(by_partition["validation"] & by_partition["test"])
        # La firma física no depende del orden de etiquetas: recalcularla
        # ordenando las posiciones debe dar el mismo identificador.
        for entry in self.manifest["entries"][:5]:
            scenario = Scenario.load(ROOT / entry["path"])
            reordered = scenario.with_victims(tuple(reversed(scenario.victims)))
            self.assertEqual(reordered.scenario_id, entry["scenario_id"])
            self.assertNotEqual(reordered.configuration_id, entry["configuration_id"])

    def test_development_examples_and_history_are_excluded(self):
        excluded = set(self.manifest["excluded_scenario_ids"])
        families = json.loads((ROOT / "configs/v2_scenario_families.json").read_text(encoding="utf-8"))
        expected = set()
        for building in families["buildings"]:
            template = Scenario.load(ROOT / building["template"])
            expected.add(template.scenario_id)
            expected |= {template.with_victims(tuple(map(tuple, positions))).scenario_id
                         for positions in building["examples"].values()}
        self.assertEqual(excluded, expected)
        ids = {e["scenario_id"] for e in self.manifest["entries"]}
        self.assertFalse(ids & excluded)
        legacy = json.loads((ROOT / "configs/scenario_splits.json").read_text(encoding="utf-8"))
        legacy_paths = {p for paths in legacy.values() for p in paths}
        self.assertFalse(legacy_paths & {e["path"] for e in self.manifest["entries"]})

    def test_no_training_configuration_uses_validation_or_test(self):
        configs = sorted((ROOT / "configs").glob("dqn_*.json"))
        self.assertTrue(configs)
        self.assertEqual(check_training_configs(MANIFEST, configs), [])

    def test_generation_is_reproducible_from_recorded_seed(self):
        for record in self.manifest["generation"]:
            with self.subTest(building=record["building"]):
                template = Scenario.load(ROOT / record["template"])
                prefix = generate_configurations(
                    template, seed=record["generation_seed"], requested=3,
                    max_attempts=record["max_attempts"])
                recorded = {e["generation_index"]: e["scenario_id"] for e in self.manifest["entries"]
                            if e["building"] == record["building"]}
                for index, item in enumerate(prefix.accepted):
                    self.assertEqual(recorded[index], item.scenario.scenario_id)

    def test_manifest_is_compatible_with_split_evaluator(self):
        for partition in ("training", "validation", "test"):
            for path in self.manifest[partition]:
                self.assertTrue((ROOT / path).exists(), path)


def tiny_config():
    return {
        "schema_version": 1,
        "manifest_id": "tiny_v1",
        "frozen_on": "2026-11-18",
        "profile": {"width": 12, "height": 12, "victims": 3},
        "output_manifest": "configs/partitions/tiny.json",
        "output_witnesses": "configs/partitions/tiny.witnesses.jsonl",
        "scenario_dir": "scenarios/partitions/tiny",
        "excluded_sources": ["configs/v2_scenario_families.json"],
        "legacy_manifests": [],
        "min_test_total": 1,
        "buildings": [{
            "key": "hub",
            "template": "scenarios/v2/coordination_hub_12x12.json",
            "generation_seed": 77,
            "split_seed": 78,
            "max_attempts": 200,
            "surplus_per_difficulty": 0,
            "quotas": {
                "training": {"easy": 1},
                "validation": {"intermediate": 1},
                "test": {"demanding": 1},
            },
        }],
    }


class BuilderTests(unittest.TestCase):
    """Construye un manifiesto mínimo en un directorio temporal."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name) / "base"
        for relative in ("scenarios/v2/coordination_hub_12x12.json",
                         "scenarios/v2/thermal_detour_12x12.json",
                         "configs/v2_scenario_families.json"):
            (cls.root / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / relative, cls.root / relative)
        cls.build = build_partitions(tiny_config(), cls.root)
        cls.manifest_path = write_partitions(cls.build, cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def copy_root(self):
        target = Path(tempfile.mkdtemp(dir=self.temp.name))
        shutil.copytree(self.root, target, dirs_exist_ok=True)
        return target, target / "configs/partitions/tiny.json"

    def rewrite(self, manifest_path, mutate, *, resign=True):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        mutate(manifest)
        if resign:
            manifest["content_sha256"] = content_sha256(manifest)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def test_tiny_build_verifies(self):
        self.assertEqual(verify_manifest(self.manifest_path, self.root), [])
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual([len(manifest[p]) for p in ("training", "validation", "test")], [1, 1, 1])
        self.assertEqual({e["difficulty"] for e in manifest["entries"] if e["partition"] == "test"},
                         {"demanding"})

    def test_build_is_deterministic(self):
        again = build_partitions(tiny_config(), self.root)
        self.assertEqual(again.manifest, self.build.manifest)
        self.assertEqual(again.witnesses, self.build.witnesses)

    def test_never_overwrites_a_frozen_manifest(self):
        with self.assertRaises(FileExistsError):
            write_partitions(self.build, self.root)

    def test_detects_modified_scenario_file(self):
        root, manifest_path = self.copy_root()
        path = root / json.loads(manifest_path.read_text(encoding="utf-8"))["test"][0]
        data = json.loads(path.read_text(encoding="utf-8"))
        data["name"] = "editado"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        problems = verify_manifest(manifest_path, root)
        self.assertTrue(any("hash distinto" in p for p in problems), problems)

    def test_detects_unsigned_manifest_edits(self):
        root, manifest_path = self.copy_root()
        self.rewrite(manifest_path, lambda m: m.update(frozen_on="2030-01-01"),
                     resign=False)
        problems = verify_manifest(manifest_path, root)
        self.assertTrue(any("content_sha256" in p for p in problems), problems)

    def test_detects_test_case_leaked_into_training(self):
        root, manifest_path = self.copy_root()

        def leak(manifest):
            test_entry = next(e for e in manifest["entries"] if e["partition"] == "test")
            duplicate = copy.deepcopy(test_entry)
            duplicate["partition"] = "training"
            manifest["entries"].append(duplicate)
            manifest["training"].append(duplicate["path"])

        self.rewrite(manifest_path, leak)
        problems = verify_manifest(manifest_path, root)
        self.assertTrue(any("scenario_id repetido" in p for p in problems), problems)
        self.assertTrue(any("cuota" in p for p in problems), problems)

    def test_detects_development_example(self):
        root, manifest_path = self.copy_root()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        first = manifest["entries"][0]["scenario_id"]
        self.rewrite(manifest_path, lambda m: m["excluded_scenario_ids"].update({first: "prueba"}))
        problems = verify_manifest(manifest_path, root)
        self.assertTrue(any("ejemplo de desarrollo" in p for p in problems), problems)

    def test_detects_changed_witness(self):
        root, manifest_path = self.copy_root()
        witnesses = root / "configs/partitions/tiny.witnesses.jsonl"
        lines = witnesses.read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])
        first["actions"] = first["actions"][:-1]
        first["steps"] -= 1
        lines[0] = json.dumps(first)
        witnesses.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.rewrite(manifest_path, lambda m: m.update(witnesses_sha256=file_sha256(witnesses)))
        problems = verify_manifest(manifest_path, root)
        self.assertTrue(any("testigo inválido" in p for p in problems), problems)

    def test_training_configuration_guard(self):
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        config = Path(tempfile.mkdtemp(dir=self.temp.name)) / "dqn_leak.json"
        config.write_text(json.dumps({
            "stages": [{"scenarios": manifest["training"] + manifest["test"]}],
            "evaluation_scenarios": manifest["test"],
        }), encoding="utf-8")
        problems = check_training_configs(self.manifest_path, [config])
        self.assertEqual(len(problems), 2)

    def test_rejects_quota_without_enough_certified_cases(self):
        config = tiny_config()
        config["buildings"][0]["max_attempts"] = 2
        config["buildings"][0]["quotas"]["training"]["easy"] = 5
        with self.assertRaisesRegex(ValueError, "reducción"):
            build_partitions(config, self.root)


if __name__ == "__main__":
    unittest.main()
