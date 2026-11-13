"""Contrato V2 de datos, varios focos y más de dos personas."""

from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.core import Action as A, RescueSimulation, Scenario


class ScenarioV2Tests(unittest.TestCase):
    def scenario(self):
        return Scenario.load(ROOT / "scenarios/v2/building_10x10.json")

    def test_multiple_sources_use_maximum_influence(self):
        scenario = self.scenario()
        self.assertEqual(scenario.victim_count, 3)
        self.assertEqual(len(scenario.heat_sources), 2)
        for position in ((6, 3), (2, 7), (3, 4), (0, 0)):
            expected = max([25] + [source.peak - source.falloff * (
                abs(position[0] - source.focus[0]) + abs(position[1] - source.focus[1]))
                for source in scenario.heat_sources])
            self.assertEqual(scenario.temperature_at(position), expected)

    def test_three_victims_require_a_second_trip(self):
        scenario = Scenario("three", 3, 3, (0, 0), ((1, 0), (0, 1), (1, 1)),
                            frozenset(), ((25.,) * 3,) * 3)
        sim = RescueSimulation(scenario)
        for actions in ((A.RIGHT, A.DOWN), (A.LEFT, A.UP)):
            sim.step(sim.encode_actions(*actions))
        self.assertEqual(len(sim.state.rescued), 2)
        self.assertEqual(sim.state.outcome, "running")
        for first in (A.RIGHT, A.DOWN, A.UP, A.LEFT):
            sim.step(sim.encode_actions(first, A.WAIT))
        self.assertEqual(sim.state.outcome, "success")
        self.assertEqual(sim.state.rescued, frozenset({0, 1, 2}))
        self.assertEqual(sim.snapshot()["victims_total"], 3)
        self.assertEqual([v["status"] for v in sim.snapshot()["victims"]], ["rescued"] * 3)

    def test_serialization_round_trip_preserves_exact_temperatures(self):
        scenario = self.scenario()
        self.assertEqual(Scenario.from_dict(scenario.to_dict()), scenario)
        directory = ROOT / "tmp/tests"
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            path = Path(temporary) / "custom.json"
            scenario.save(path)
            self.assertEqual(Scenario.load(path), scenario)
            with self.assertRaises(FileExistsError):
                scenario.save(path)

    def test_custom_positions_do_not_mutate_template(self):
        scenario = self.scenario()
        custom = scenario.with_victims(((1, 0), (0, 1), (1, 1)), name="custom")
        self.assertEqual(scenario.victims, ((8, 1), (1, 8), (8, 8)))
        self.assertEqual(custom.temperatures, scenario.temperatures)
        self.assertNotEqual(custom.fingerprint(), scenario.fingerprint())
        self.assertEqual(custom.fingerprint(), replace(custom, name="other").fingerprint())
        self.assertEqual(custom.fingerprint(), custom.with_victims(reversed(custom.victims)).fingerprint())
        self.assertNotEqual(custom.configuration_id,
                            custom.with_victims(reversed(custom.victims)).configuration_id)

    def test_bad_input_and_stale_fingerprints_are_rejected(self):
        scenario = self.scenario()
        for changes in (dict(width=True), dict(victims=[[1.5, 0]]), dict(victims=[]),
                        dict(victims=[[1, 0], [1, 0]]), dict(base=[0, False]),
                        dict(scenario_id="incorrect"), dict(schema_version=99)):
            data = {**scenario.to_dict(), **changes}
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                Scenario.from_dict(data)

    def test_legacy_heat_files_keep_their_values(self):
        scenario = Scenario.load(ROOT / "scenarios/demo.json")
        self.assertEqual(scenario.temperature_at((3, 1)), 90)
        self.assertEqual(scenario.temperature_at((0, 0)), 25)
        self.assertEqual(scenario.victim_count, 2)


if __name__ == "__main__":
    unittest.main()
