"""Certificación acotada y reproducción de trayectorias testigo reales."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.core import (
    Scenario,
    ViabilityCertificate,
    ViabilityResult,
    ViabilityStatus,
    certify_viability,
    replay_certificate,
)


class ViabilityTests(unittest.TestCase):
    def scenario(self):
        return Scenario.load(ROOT / "scenarios/v2/building_10x10.json")

    def test_known_v2_scenario_is_certified_with_auditable_witness(self):
        scenario = self.scenario()
        result = certify_viability(scenario)
        self.assertEqual(result.status, ViabilityStatus.CERTIFIED)
        self.assertIsNotNone(result.certificate)
        certificate = result.certificate
        self.assertEqual(certificate.strategy, "thermal")
        self.assertEqual(certificate.rescued, 3)
        self.assertEqual(certificate.outcome, "success")
        self.assertLessEqual(certificate.steps, scenario.max_steps)
        self.assertEqual(len(certificate.actions), certificate.steps)
        self.assertTrue(all(value > 0 for value in certificate.final_integrities))
        self.assertEqual(len(result.attempts), 1)

    def test_structurally_invalid_input_has_distinct_status(self):
        data = self.scenario().to_dict()
        data["walls"] += [[1, 0], [0, 1]]
        data.pop("scenario_id")
        data.pop("configuration_id")
        result = certify_viability(data)
        self.assertEqual(result.status, ViabilityStatus.STRUCTURAL_INVALID)
        self.assertIsNone(result.scenario_id)
        self.assertIsNone(result.certificate)

    def test_connected_scenario_with_tiny_budget_is_not_certified(self):
        result = certify_viability(self.scenario(), action_budget=1)
        self.assertEqual(result.status, ViabilityStatus.NOT_CERTIFIED)
        self.assertIn("no demuestra imposibilidad", result.message)
        self.assertEqual(result.attempts[0].actions_executed, 1)
        self.assertIsNone(result.certificate)

    def test_zero_budget_is_defined_and_executes_no_actions(self):
        result = certify_viability(self.scenario(), action_budget=0)
        self.assertEqual(result.status, ViabilityStatus.NOT_CERTIFIED)
        self.assertEqual([attempt.actions_executed for attempt in result.attempts], [0, 0])
        self.assertTrue(all(attempt.outcome == "running" for attempt in result.attempts))

    def test_certified_witness_replays_through_rescue_simulation(self):
        scenario = self.scenario()
        result = certify_viability(scenario)
        state = replay_certificate(scenario, result.certificate)
        self.assertEqual(state.outcome, "success")
        self.assertEqual(len(state.rescued), 3)
        self.assertEqual(state.steps, result.certificate.steps)
        self.assertEqual(sum(r.damage for r in state.robots), result.certificate.damage_total)
        self.assertEqual(tuple(r.integrity for r in state.robots), result.certificate.final_integrities)

    def test_witness_from_another_scenario_or_configuration_is_rejected(self):
        scenario = self.scenario()
        certificate = certify_viability(scenario).certificate
        different_scenario = scenario.with_victims(((1, 0), (0, 1), (1, 1)))
        with self.assertRaisesRegex(ValueError, "scenario_id"):
            replay_certificate(different_scenario, certificate)
        relabeled = scenario.with_victims(reversed(scenario.victims))
        self.assertEqual(relabeled.scenario_id, scenario.scenario_id)
        with self.assertRaisesRegex(ValueError, "configuration_id"):
            replay_certificate(relabeled, certificate)

    def test_heuristic_failure_is_not_reported_as_impossible(self):
        class FailingPolicy:
            def act(self, state):
                raise ValueError("fallo deliberado de la heurística")

        with patch("sar_bot.agents.factory.create_policy", return_value=FailingPolicy()):
            result = certify_viability(self.scenario(), strategies=("shortest",), action_budget=10)
        self.assertEqual(result.status.value, "not_certified")
        self.assertNotIn("imposible", result.status.value)
        self.assertEqual(result.attempts[0].outcome, "running")
        self.assertIn("fallo deliberado", result.attempts[0].error)

    def test_result_preserves_both_scenario_identifiers(self):
        scenario = self.scenario()
        result = certify_viability(scenario)
        self.assertEqual(result.scenario_id, scenario.scenario_id)
        self.assertEqual(result.configuration_id, scenario.configuration_id)
        self.assertEqual(result.certificate.scenario_id, scenario.scenario_id)
        self.assertEqual(result.certificate.configuration_id, scenario.configuration_id)

    def test_dqn_and_invalid_budgets_are_rejected(self):
        for kwargs in (
            {"strategies": ("dqn",)}, {"action_budget": True}, {"action_budget": -1},
            {"action_budget": 1.5}, {"action_budget": "1"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                certify_viability(self.scenario(), **kwargs)

    def test_public_result_types_reject_contradictory_states(self):
        scenario = self.scenario()
        certificate = certify_viability(scenario).certificate
        with self.assertRaises(ValueError):
            ViabilityResult(ViabilityStatus.CERTIFIED, "contradictorio")
        with self.assertRaises(ValueError):
            ViabilityResult(
                ViabilityStatus.NOT_CERTIFIED, "contradictorio",
                scenario.scenario_id, scenario.configuration_id, certificate,
            )
        with self.assertRaises(ValueError):
            ViabilityCertificate(
                "thermal", scenario.scenario_id, scenario.configuration_id,
                1, 3, 0, (100, 100), (), "success",
            )


if __name__ == "__main__":
    unittest.main()
