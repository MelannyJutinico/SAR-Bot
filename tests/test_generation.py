"""Generación V2 reproducible, diversa, certificada y siempre acotada."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.core import Difficulty, Scenario, ViabilityStatus, generate_configurations


class GenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coordination = Scenario.load(ROOT / "scenarios/v2/coordination_hub_12x12.json")
        cls.detour = Scenario.load(ROOT / "scenarios/v2/thermal_detour_12x12.json")
        cls.first = generate_configurations(
            cls.coordination, seed=2026, requested=3, max_attempts=40
        )
        cls.repeated = generate_configurations(
            cls.coordination, seed=2026, requested=3, max_attempts=40
        )
        cls.other_seed = generate_configurations(
            cls.coordination, seed=2027, requested=3, max_attempts=40
        )
        cls.other_building = generate_configurations(
            cls.detour, seed=2026, requested=3, max_attempts=40
        )

    def test_same_seed_reproduces_positions_ids_and_statistics(self):
        self.assertEqual(self.first.to_dict(), self.repeated.to_dict())
        self.assertEqual(self.first.generated_ids, self.repeated.generated_ids)
        self.assertEqual(
            [item.scenario.configuration_id for item in self.first.accepted],
            [item.scenario.configuration_id for item in self.repeated.accepted],
        )

    def test_different_seed_changes_generated_cases(self):
        self.assertNotEqual(self.first.generated_ids, self.other_seed.generated_ids)

    def test_both_buildings_generate_three_valid_certified_people_and_all_families(self):
        for template, summary in (
            (self.coordination, self.first), (self.detour, self.other_building),
        ):
            with self.subTest(template=template.name):
                self.assertEqual(summary.accepted_count, 3)
                self.assertEqual(
                    {item.difficulty for item in summary.accepted}, set(Difficulty)
                )
                for item in summary.accepted:
                    scenario = item.scenario
                    self.assertEqual(len(scenario.victims), 3)
                    self.assertEqual(len(set(scenario.victims)), 3)
                    self.assertNotIn(scenario.base, scenario.victims)
                    self.assertFalse(set(scenario.victims) & scenario.walls)
                    self.assertTrue(all(scenario.in_bounds(position) for position in scenario.victims))
                    self.assertEqual(item.viability.status, ViabilityStatus.CERTIFIED)
                    self.assertEqual(scenario.walls, template.walls)
                    self.assertEqual(scenario.temperatures, template.temperatures)
                    self.assertEqual(scenario.heat_sources, template.heat_sources)
                    self.assertEqual(scenario.max_steps, template.max_steps)

    def test_permuted_labels_are_one_physical_case_and_count_as_duplicate(self):
        easy = ((2, 1), (1, 2), (3, 2))
        intermediate = ((10, 1), (1, 10), (6, 5))
        first = self.coordination.with_victims(easy)
        relabeled = self.coordination.with_victims(reversed(easy))
        self.assertEqual(first.scenario_id, relabeled.scenario_id)
        self.assertNotEqual(first.configuration_id, relabeled.configuration_id)
        samples = [list(easy), list(reversed(easy)), list(intermediate)]
        with patch("sar_bot.core.generation.random.Random.sample", side_effect=samples):
            summary = generate_configurations(
                self.coordination, seed=1, requested=2, max_attempts=3,
                difficulties=(Difficulty.EASY, Difficulty.INTERMEDIATE),
            )
        self.assertEqual(summary.accepted_count, 2)
        self.assertEqual(summary.duplicates, 1)

    def test_attempt_limit_and_not_certified_cases_are_reported_separately(self):
        summary = generate_configurations(
            self.coordination, seed=2026, requested=3, max_attempts=2, action_budget=0
        )
        self.assertEqual(summary.attempts, 2)
        self.assertEqual(summary.accepted_count, 0)
        self.assertGreaterEqual(len(summary.not_certified), 1)
        self.assertTrue(all(item.viability.status is ViabilityStatus.NOT_CERTIFIED
                            for item in summary.not_certified))

    def test_disconnected_sample_is_counted_as_structural_invalid(self):
        disconnected = Scenario(
            "disconnected_candidate", 4, 4, (0, 0), ((1, 0), (0, 1), (1, 1)),
            frozenset({(2, 3), (3, 2)}), ((25.0,) * 4,) * 4,
        )
        sample = [[(3, 3), (1, 0), (0, 1)]]
        with patch("sar_bot.core.generation.random.Random.sample", side_effect=sample):
            summary = generate_configurations(
                disconnected, seed=1, requested=1, max_attempts=1,
            )
        self.assertEqual(summary.attempts, 1)
        self.assertEqual(summary.structural_invalid, 1)
        self.assertEqual(summary.accepted_count, 0)

    def test_certification_never_requests_dqn(self):
        from sar_bot.agents.factory import create_policy as real_create_policy
        strategies = []

        def recording_factory(simulation, strategy, **kwargs):
            strategies.append(strategy)
            return real_create_policy(simulation, strategy, **kwargs)

        with patch("sar_bot.agents.factory.create_policy", side_effect=recording_factory):
            summary = generate_configurations(
                self.coordination, seed=8, requested=1, max_attempts=20
            )
        self.assertEqual(summary.accepted_count, 1)
        self.assertTrue(strategies)
        self.assertNotIn("dqn", strategies)

    def test_invalid_requests_are_rejected(self):
        for kwargs in (
            {"seed": True, "requested": 1, "max_attempts": 1},
            {"seed": 1, "requested": 0, "max_attempts": 1},
            {"seed": 1, "requested": 1, "max_attempts": 0},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                generate_configurations(self.coordination, **kwargs)


if __name__ == "__main__":
    unittest.main()
