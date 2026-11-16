"""Reglas críticas del motor (docs/PLAN_DE_TRABAJO.md, "Verificaciones necesarias")."""

import pytest

from sar_bot.core import (
    Action,
    Outcome,
    RescueSim,
    RulesConfig,
    Scenario,
    VictimStatus,
    encode_joint,
    load_layouts,
    temperature_field,
)

U, D, L, R, W = Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT, Action.WAIT

CORRIDOR = """
B.....
......
"""


def run(sim, actions_0, actions_1):
    """Ejecuta dos secuencias de acciones (se rellena con WAIT) y devuelve los resultados."""
    n = max(len(actions_0), len(actions_1))
    a0 = list(actions_0) + [W] * (n - len(actions_0))
    a1 = list(actions_1) + [W] * (n - len(actions_1))
    return [sim.step(x, y) for x, y in zip(a0, a1)]


def test_esperar_en_celda_caliente_causa_dano_en_cada_paso(scenario_factory):
    scenario = scenario_factory(CORRIDOR, [(1, 5), (1, 4)], hot={(0, 2): 65.0}, starts=[(0, 2), (0, 0)])
    sim = RescueSim(scenario)
    integrities = []
    for _ in range(4):
        sim.step(W, W)
        integrities.append(sim.robots[0].integrity)
    assert integrities == [95.0, 90.0, 85.0, 80.0]


def test_cuatro_pasos_a_65_grados_causan_20_de_dano(scenario_factory):
    scenario = scenario_factory(CORRIDOR, [(1, 5), (1, 4)], hot={(0, 2): 65.0}, starts=[(0, 2), (0, 0)])
    sim = RescueSim(scenario)
    run(sim, [W] * 4, [W] * 4)
    assert sim.robots[0].damage_taken == 20.0
    assert sim.robots[0].integrity == 80.0
    assert sim.robots[1].damage_taken == 0.0


def test_ambos_robots_reciben_exposicion_exactamente_una_vez_por_paso(scenario_factory):
    scenario = scenario_factory(
        CORRIDOR, [(1, 5), (0, 5)], hot={(0, 2): 65.0, (1, 3): 45.0}, starts=[(0, 2), (1, 3)]
    )
    sim = RescueSim(scenario)
    results = run(sim, [W] * 3, [W] * 3)
    assert [r.damage for r in results] == [(5.0, 2.0)] * 3
    assert (sim.robots[0].damage_taken, sim.robots[1].damage_taken) == (15.0, 6.0)


def test_colisiones_no_detienen_el_reloj_ni_duplican_exposicion(scenario_factory):
    scenario = scenario_factory(
        CORRIDOR,
        [(1, 5), (1, 4)],
        hot={(0, 2): 65.0, (0, 4): 65.0, (0, 3): 85.0},
        starts=[(0, 2), (0, 4)],
    )
    sim = RescueSim(scenario)
    # Tres pasos intentando entrar en la misma celda, uno contra el límite del mapa.
    results = run(sim, [R, R, R, U], [L, L, L, W])
    assert [r.step for r in results] == [1, 2, 3, 4]
    assert [r.blocked_by_robot for r in results[:3]] == [(True, True)] * 3
    assert results[3].blocked_by_wall == (True, False)
    assert all(r.damage == (5.0, 5.0) for r in results)
    assert sim.positions == ((0, 2), (0, 4))
    assert (sim.robots[0].damage_taken, sim.robots[1].damage_taken) == (20.0, 20.0)


def test_una_victima_no_se_recoge_ni_entrega_dos_veces(scenario_factory):
    scenario = scenario_factory(CORRIDOR, [(0, 1), (0, 3)], starts=[(0, 0), (1, 5)])
    sim = RescueSim(scenario)
    results = run(sim, [R, L, R], [])
    assert results[0].picked_up == (0, None)
    assert results[1].delivered == (0, None)
    # Volver a la celda original de la víctima 0 no la recoge otra vez.
    assert results[2].picked_up == (None, None)
    assert sim.robots[0].carrying is None
    assert sim.victims[0].status is VictimStatus.RESCUED

    results += run(sim, [R, R, L, L, L], [])
    picked = [r.picked_up[0] for r in results if r.picked_up[0] is not None]
    delivered = [r.delivered[0] for r in results if r.delivered[0] is not None]
    assert picked == [0, 1]
    assert delivered == [0, 1]
    assert sim.rescued_count == 2
    assert sim.outcome is Outcome.SUCCESS


def test_capacidad_de_una_victima_por_robot(scenario_factory):
    scenario = scenario_factory(CORRIDOR, [(0, 1), (0, 2)], starts=[(0, 0), (1, 5)])
    sim = RescueSim(scenario)
    results = run(sim, [R, R], [])
    assert results[1].picked_up == (None, None)
    assert sim.robots[0].carrying == 0
    assert sim.victims[1].status is VictimStatus.WAITING


def _final_delivery_scenario(scenario_factory):
    # El robot 0 rescata ambas víctimas en 4 pasos; el robot 1 espera en una celda a 85 °C (tasa 10).
    return scenario_factory(CORRIDOR, [(0, 1), (1, 0)], hot={(1, 5): 85.0}, starts=[(0, 0), (1, 5)])


def test_la_destruccion_tiene_prioridad_sobre_la_entrega_del_mismo_paso(scenario_factory):
    sim = RescueSim(_final_delivery_scenario(scenario_factory), RulesConfig(initial_integrity=40.0))
    results = run(sim, [R, L, D, U], [])
    last = results[-1]
    assert last.step == 4
    assert sim.robots[1].integrity == 0.0
    assert last.outcome is Outcome.DESTROYED
    assert last.terminated and not last.truncated
    assert last.delivered == (None, None)
    assert sim.rescued_count == 1
    assert sim.victims[1].status is VictimStatus.CARRIED


def test_exito_en_el_ultimo_paso_permitido_es_exito(scenario_factory):
    rules = RulesConfig(initial_integrity=50.0, max_steps=4)
    sim = RescueSim(_final_delivery_scenario(scenario_factory), rules)
    results = run(sim, [R, L, D, U], [])
    last = results[-1]
    assert last.step == rules.max_steps
    assert last.outcome is Outcome.SUCCESS
    assert last.terminated and not last.truncated
    assert sim.robots[1].integrity == 10.0


def test_limite_de_pasos_se_distingue_de_exito_y_fracaso(scenario_factory):
    scenario = scenario_factory(CORRIDOR, [(1, 5), (1, 4)])
    sim = RescueSim(scenario, RulesConfig(max_steps=3))
    results = run(sim, [W] * 3, [W] * 3)
    assert [r.outcome for r in results] == [Outcome.RUNNING, Outcome.RUNNING, Outcome.TIMEOUT]
    assert results[-1].truncated and not results[-1].terminated
    assert sim.episode_metrics()["success"] is False


def test_no_se_puede_avanzar_un_episodio_terminado(scenario_factory):
    sim = RescueSim(scenario_factory(CORRIDOR, [(1, 5), (1, 4)]), RulesConfig(max_steps=1))
    sim.step(W, W)
    with pytest.raises(RuntimeError):
        sim.step(W, W)


def test_reset_restaura_el_estado_inicial(scenario_factory):
    scenario = scenario_factory(CORRIDOR, [(0, 1), (1, 4)], hot={(0, 1): 65.0})
    sim = RescueSim(scenario)
    run(sim, [R], [D])
    sim.reset()
    assert sim.step_count == 0
    assert sim.outcome is Outcome.RUNNING
    assert sim.positions == ((0, 0), (0, 0))
    assert all(r.integrity == 100.0 and r.carrying is None for r in sim.robots)
    assert all(v.status is VictimStatus.WAITING for v in sim.victims)


def test_step_joint_equivale_a_step(scenario_factory):
    scenario = scenario_factory(CORRIDOR, [(1, 5), (1, 4)])
    a, b = RescueSim(scenario), RescueSim(scenario)
    assert a.step(R, D) == b.step_joint(encode_joint(R, D))


def _full_mission():
    layout = load_layouts()["edificio_a"]
    scenario = Scenario(
        layout=layout,
        victims=((0, 5), (2, 2)),
        temperatures=temperature_field(layout, hotspot=(2, 4)),
        hotspot=(2, 4),
        scenario_id="edificio_a/manual",
    )
    sim = RescueSim(scenario)
    results = run(sim, [R] * 5 + [L] * 5, [D, D, R, R, L, L, U, U])
    return sim, results


def test_mision_completa_reproducible():
    sim, results = _full_mission()
    assert sim.outcome is Outcome.SUCCESS
    assert sim.step_count == 10
    assert results[4].picked_up == (0, None)
    assert results[3].picked_up == (None, 1)
    assert results[7].delivered == (None, 1)
    assert results[9].delivered == (0, None)
    # Celdas a 55 °C (tasa 2): el robot 0 pasa dos veces por (0, 4); el robot 1 recoge en (2, 2).
    assert (sim.robots[0].damage_taken, sim.robots[1].damage_taken) == (4.0, 2.0)

    sim_again, results_again = _full_mission()
    assert results_again == results
    assert sim_again.episode_metrics() == sim.episode_metrics()


def test_vista_de_texto(scenario_factory):
    sim = RescueSim(scenario_factory(CORRIDOR, [(0, 2), (1, 4)]))
    text = sim.to_text()
    assert "paso 0/100" in text
    assert text.splitlines()[1] == "*.v..."
