import numpy as np
import pytest

from sar_bot.core import (
    Layout,
    RulesConfig,
    estimate_viability,
    generate_scenario,
    load_layouts,
    manhattan,
    min_damage_path,
)

LAYOUTS = load_layouts()


def test_planos_cargan_y_son_conexos():
    assert {"edificio_a", "edificio_b", "edificio_c"} <= set(LAYOUTS)
    for layout in LAYOUTS.values():
        assert layout.shape == (6, 6)
        assert layout.is_connected()


@pytest.mark.parametrize("name", sorted(LAYOUTS))
def test_la_misma_semilla_reproduce_el_escenario(name):
    a = generate_scenario(LAYOUTS[name], seed=123)
    b = generate_scenario(LAYOUTS[name], seed=123)
    assert a.victims == b.victims
    assert a.hotspot == b.hotspot
    assert a.scenario_id == b.scenario_id
    assert np.array_equal(a.temperatures, b.temperatures)


def test_semillas_distintas_producen_escenarios_distintos():
    layout = LAYOUTS["edificio_a"]
    variants = {(s.victims, s.hotspot) for s in (generate_scenario(layout, seed) for seed in range(20))}
    assert len(variants) > 10


@pytest.mark.parametrize("name", sorted(LAYOUTS))
def test_escenarios_generados_cumplen_restricciones(name):
    layout = LAYOUTS[name]
    distances = layout.distances_from(layout.base)
    for seed in range(50):
        scenario = generate_scenario(layout, seed)
        assert len(set(scenario.victims)) == 2
        assert all(distances[v] >= 2 for v in scenario.victims)
        assert manhattan(scenario.hotspot, layout.base) >= 3
        assert scenario.temperature_at(layout.base) == 25.0
        assert scenario.robot_starts == (layout.base, layout.base)
        assert estimate_viability(scenario)


def test_camino_de_menor_dano_rodea_el_calor(scenario_factory):
    scenario = scenario_factory("B...\n.##.\n....", [(2, 3), (2, 0)], hot={(0, 2): 85.0})
    rules = RulesConfig()
    cost = min_damage_path(scenario.layout, scenario.temperatures, rules, (0, 0), (0, 3))
    assert cost == (0.0, 7)


def test_camino_inalcanzable():
    layout = Layout.from_text("t", "B#.")
    assert min_damage_path(layout, np.zeros(layout.shape), RulesConfig(), (0, 0), (0, 2)) is None


def test_viabilidad_detecta_calor_letal(scenario_factory):
    victims = [(0, 5), (0, 4)]
    hot_cells = {(0, c): 85.0 for c in range(1, 6)}  # tasa 10
    scenario = scenario_factory("B.....", victims, hot=hot_cells)
    # Rescatar (0, 5): 5 pasos de ida y 4 de vuelta en calor (la base es segura) = 90 de daño.
    assert estimate_viability(scenario, RulesConfig(initial_integrity=91.0))
    # Con integridad 90 el robot terminaría exactamente en 0 ⇒ destruido ⇒ no viable.
    assert not estimate_viability(scenario, RulesConfig(initial_integrity=90.0))

    longer = scenario_factory("B......", [(0, 6), (0, 5)], hot={(0, c): 85.0 for c in range(1, 7)})
    assert not estimate_viability(longer)  # 6 + 5 pasos a tasa 10 = 110 ≥ 100


def test_viabilidad_respeta_el_limite_de_pasos(scenario_factory):
    scenario = scenario_factory("B.....", [(0, 5), (0, 4)])
    assert estimate_viability(scenario, RulesConfig(max_steps=10))
    assert not estimate_viability(scenario, RulesConfig(max_steps=9))


@pytest.mark.parametrize(
    "layout_text, victims, starts",
    [
        ("B#.\n...", [(0, 1), (1, 2)], None),  # víctima sobre obstáculo
        ("B..\n...", [(0, 0), (1, 2)], None),  # víctima en la base
        ("B..\n...", [(1, 2), (1, 2)], None),  # víctimas repetidas
        ("B#.\n.#.", [(0, 2), (1, 0)], None),  # víctima inalcanzable
        ("B..\n...", [(0, 2), (1, 2)], [(1, 1), (1, 1)]),  # robots comparten celda fuera de la base
        ("B..\n...", [(0, 2), (1, 2)], [(0, 2), (0, 0)]),  # robot empieza sobre una víctima
    ],
)
def test_escenarios_invalidos_se_rechazan(scenario_factory, layout_text, victims, starts):
    with pytest.raises(ValueError):
        scenario_factory(layout_text, victims, starts=starts)
