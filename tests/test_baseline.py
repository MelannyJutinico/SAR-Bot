"""Estrategia de referencia y evaluación por episodio."""

import csv

import pytest

from sar_bot.agents import RandomPolicy, ShortestPathBaseline
from sar_bot.config import load_config
from sar_bot.core import Action, RescueSim, decode_joint
from sar_bot.evaluation import evaluate, summarize, write_csv


def test_la_referencia_completa_un_escenario_viable(scenario_factory):
    scenario = scenario_factory("B.....\n.#.#..\n......", [(2, 5), (0, 4)])
    sim = RescueSim(scenario)
    policy = ShortestPathBaseline()
    policy.reset(sim)
    while not sim.done:
        sim.step_joint(policy.act(None, sim))
    assert sim.outcome.value == "exito"


def test_la_referencia_se_aparta_en_un_pasillo(scenario_factory):
    # Pasillo de una celda con un hueco lateral en (1, 2): el robot 1 vuelve cargado
    # hacia la base mientras el robot 0 avanza por el mismo pasillo.
    scenario = scenario_factory(
        "B.....\n##.###",
        [(0, 5), (0, 3)],
        starts=[(0, 0), (0, 4)],
    )
    sim = RescueSim(scenario)
    policy = ShortestPathBaseline()
    policy.reset(sim)
    while not sim.done:
        sim.step_joint(policy.act(None, sim))
    assert sim.outcome.value == "exito"
    assert sim.step_count <= 20


def test_la_referencia_asigna_victimas_distintas(scenario_factory):
    scenario = scenario_factory("B.....\n......", [(0, 5), (1, 5)])
    sim = RescueSim(scenario)
    policy = ShortestPathBaseline()
    policy.reset(sim)
    targets = policy.targets(sim)
    assert sorted(targets) == [(0, 5), (1, 5)]
    a0, a1 = decode_joint(policy.act(None, sim))
    assert {a0, a1} == {Action.RIGHT, Action.DOWN}


@pytest.mark.parametrize("config_name", ["una_victima", "sin_calor", "base"])
def test_la_referencia_completa_toda_la_validacion(config_name):
    rows = evaluate(ShortestPathBaseline(), load_config(f"configs/{config_name}.toml"), "validation")
    summary = summarize(rows)
    assert summary["episodes"] == 150
    assert summary["success_rate"] == 1.0


def test_filas_de_evaluacion_y_csv(tmp_path):
    rows = evaluate(RandomPolicy(seed=1), load_config(), "validation", limit=5)
    assert len(rows) == 5
    expected = {
        "strategy", "split", "layout", "scenario_id", "seed", "outcome", "success", "rescued",
        "steps", "damage_r0", "damage_r1", "damage_total", "integrity_r0", "integrity_r1", "return",
    }
    assert expected <= set(rows[0])
    assert all(r["strategy"] == "aleatoria" and r["split"] == "validation" for r in rows)

    path = write_csv(rows, tmp_path / "eval.csv")
    with path.open(encoding="utf-8") as handle:
        loaded = list(csv.DictReader(handle))
    assert [r["scenario_id"] for r in loaded] == [r["scenario_id"] for r in rows]


def test_resumen_compara_duracion_solo_entre_exitos():
    rows = [
        {"success": True, "outcome": "exito", "rescued": 2, "damage_total": 10.0, "steps": 20, "return": 30.0},
        {"success": False, "outcome": "robot_destruido", "rescued": 0, "damage_total": 100.0, "steps": 3, "return": -25.0},
    ]
    summary = summarize(rows)
    assert summary["success_rate"] == 0.5
    assert summary["steps_mean"] == 11.5
    assert summary["steps_mean_success"] == 20.0
    assert summary["damage_total_mean_success"] == 10.0
