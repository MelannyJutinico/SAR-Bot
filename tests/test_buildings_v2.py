"""Edificios finales 12x12, familias y calibración térmica medida."""

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.agents import create_policy
from sar_bot.core import (
    Difficulty, RescueSimulation, Scenario, ViabilityStatus,
    certify_viability, classify_difficulty,
)
from sar_bot.evaluation import evaluate_episode


class BuildingsV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads((ROOT / "configs/v2_scenario_families.json").read_text(encoding="utf-8"))
        cls.buildings = []
        for entry in manifest["buildings"]:
            template = Scenario.load(ROOT / entry["template"])
            cls.buildings.append((entry, template))

    @staticmethod
    def evaluate(scenario, strategy):
        simulation = RescueSimulation(scenario)
        return evaluate_episode(simulation, create_policy(simulation, strategy), strategy)

    def test_two_distinct_structured_templates_are_valid_and_certified(self):
        self.assertEqual(len(self.buildings), 2)
        self.assertEqual(len({template.scenario_id for _, template in self.buildings}), 2)
        for entry, template in self.buildings:
            with self.subTest(template=entry["template"]):
                self.assertEqual((template.width, template.height, template.victim_count), (12, 12, 3))
                self.assertGreaterEqual(len(template.walls), 18)
                self.assertGreaterEqual(len(template.heat_sources), 2)
                self.assertEqual(template.temperature_at(template.base), template.ambient_temperature)
                result = certify_viability(template)
                self.assertEqual(result.status, ViabilityStatus.CERTIFIED)
                self.assertEqual(result.certificate.rescued, 3)

    def test_manifest_examples_match_each_documented_difficulty(self):
        expected = {value.value for value in Difficulty}
        for entry, template in self.buildings:
            self.assertEqual(set(entry["examples"]), expected)
            for level, positions in entry["examples"].items():
                with self.subTest(template=entry["template"], level=level):
                    scenario = template.with_victims(positions)
                    self.assertEqual(classify_difficulty(template, scenario.victims).value, level)
                    self.assertEqual(certify_viability(scenario).status, ViabilityStatus.CERTIFIED)

    def test_exported_heat_field_matches_static_maximum_influence(self):
        for entry, template in self.buildings:
            for y in range(template.height):
                for x in range(template.width):
                    expected = max([template.ambient_temperature] + [
                        source.peak - source.falloff * (
                            abs(x - source.focus[0]) + abs(y - source.focus[1])
                        ) for source in template.heat_sources
                    ])
                    with self.subTest(template=entry["template"], position=(x, y)):
                        self.assertEqual(template.temperature_at((x, y)), expected)

    def test_coordination_building_measures_longer_safer_thermal_route(self):
        entry, template = self.buildings[0]
        scenario = template.with_victims(entry["examples"]["demanding"])
        shortest = self.evaluate(scenario, "shortest")
        thermal = self.evaluate(scenario, "thermal")
        self.assertTrue(shortest["success"] and thermal["success"])
        self.assertLess(shortest["steps"], thermal["steps"])
        self.assertGreater(shortest["damage_total"], thermal["damage_total"])

    def test_detour_building_has_successful_direct_and_safer_routes(self):
        entry, template = self.buildings[1]
        scenario = template.with_victims(entry["examples"]["intermediate"])
        shortest = self.evaluate(scenario, "shortest")
        thermal = self.evaluate(scenario, "thermal")
        self.assertTrue(shortest["success"] and thermal["success"])
        self.assertLess(shortest["steps"], thermal["steps"])
        self.assertGreater(shortest["damage_total"], thermal["damage_total"])
        self.assertTrue(all(0 < shortest[key] < 100 for key in
                            ("integrity_robot_1", "integrity_robot_2")))


if __name__ == "__main__":
    unittest.main()
