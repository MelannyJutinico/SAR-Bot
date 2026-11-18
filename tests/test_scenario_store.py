"""Persistencia oficial, aislamiento de rutas e identidad exacta."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sar_bot.core import Scenario
from sar_bot.ui.scenario_store import ScenarioStore
from sar_bot.ui.playback import prepare_episode


class ScenarioStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ScenarioStore(Path(self.temp.name) / "personal")
        self.scenario = Scenario.load(ROOT / "scenarios/v2/warmup_10x10.json").with_victims(((2,0),(0,2),(1,1)))

    def tearDown(self):self.temp.cleanup()

    def test_save_load_exact_roundtrip_and_deterministic_episode(self):
        path = self.store.save(self.scenario)
        loaded = self.store.load(path.name)
        self.assertEqual(loaded.to_dict(), self.scenario.to_dict())
        self.assertEqual(loaded.configuration_id, self.scenario.configuration_id)
        self.assertEqual(loaded.scenario_id, self.scenario.scenario_id)
        self.assertEqual(loaded.victims, ((2,0),(0,2),(1,1)))
        self.assertEqual(prepare_episode(loaded,"shortest").states,
                         prepare_episode(self.scenario,"shortest").states)
        self.assertEqual(self.store.list_files(), (path.name,))

    def test_permuted_people_have_distinct_files_and_exact_order(self):
        other = self.scenario.with_victims(reversed(self.scenario.victims))
        first, second = self.store.save(self.scenario), self.store.save(other)
        self.assertNotEqual(first, second)
        self.assertEqual(self.store.load(second.name).victims, other.victims)
        self.assertEqual(other.scenario_id, self.scenario.scenario_id)

    def test_existing_file_is_not_overwritten(self):
        path = self.store.save(self.scenario); before = path.read_bytes()
        with self.assertRaises(FileExistsError):self.store.save(self.scenario)
        self.assertEqual(before, path.read_bytes())

    def test_invalid_directory_and_missing_file(self):
        blocker = Path(self.temp.name) / "blocker"; blocker.write_text("file")
        with self.assertRaises(OSError):ScenarioStore(blocker).save(self.scenario)
        with self.assertRaises(FileNotFoundError):self.store.load("missing.json")

    def test_corrupt_structural_invalid_and_incompatible_json(self):
        self.store.directory.mkdir()
        path = self.store.directory / "bad.json"
        for data in ("{", json.dumps({"width":10}),
                     json.dumps(Scenario.load(ROOT / "scenarios/demo.json").to_dict())):
            path.write_text(data,encoding="utf-8")
            with self.assertRaises(ValueError):self.store.load(path.name)

    def test_paths_cannot_escape_personal_directory(self):
        for name in ("../outside.json", str(ROOT / "scenarios/demo.json"), "file.txt"):
            with self.assertRaises(ValueError):self.store.load(name)

    def test_listing_does_not_create_directory_or_include_other_files(self):
        self.assertEqual(self.store.list_files(), ())
        self.assertFalse(self.store.directory.exists())
        path = self.store.save(self.scenario)
        (self.store.directory / "notes.txt").write_text("not a scenario")
        self.assertEqual(self.store.list_files(), (path.name,))


if __name__ == "__main__":unittest.main()
