"""Comprueba una actualización real en una sesión aislada, sin usar prueba."""
import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.core import Scenario
from sar_bot.online import LearningSession, digest
from record_online_evidence import parameter_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/learning-guard.json")
    args = parser.parse_args()
    base = ROOT / "artifacts/final/model.zip"
    scenario = Scenario.load(ROOT / "scenarios/partitions/v2_12x12/training/hub_training_01_easy.json")
    configured = LearningSession.for_project(ROOT, base, scenario)
    session = LearningSession(ROOT / "outputs/guard_checks" / uuid4().hex, base,
                              protected_ids=configured.protected_ids,
                              control_scenarios=configured.control_scenarios)
    original = digest(base)
    q_before = parameter_hash(base)
    episode = session.prepare_episode(scenario)
    result = session.learn_episode(episode)
    current = session.snapshot()
    q_after = parameter_hash(current.model_path)
    evidence = {"scope": "One new training mission; only training controls plus that mission; no test evaluation",
                "base_sha256": original, "base_unchanged": digest(base) == original,
                "q_before": q_before, "q_after": q_after,
                "result": result}
    assert evidence["base_unchanged"]
    if not result["last_guard"]["accepted"]:
        assert q_before == q_after
    assert result["missions"] == 1 and result["buffer_size"] == len(episode.actions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({"guard": result["last_guard"], "missions": result["missions"],
                      "experiences": result["buffer_size"], "accepted_updates": result["updates"],
                      "base_unchanged": evidence["base_unchanged"]}))


if __name__ == "__main__":
    main()
