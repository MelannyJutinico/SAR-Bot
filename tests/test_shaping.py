"""Guía por potencial: F = γ·Φ(s') − Φ(s), Φ = −coeficiente × trabajo pendiente."""

import dataclasses

import pytest

from sar_bot.config import load_config
from sar_bot.core import Action, RescueSim, Scenario, encode_joint, load_layouts, temperature_field
from sar_bot.env import RescueEnv
from sar_bot.env.shaping import DistanceCache, remaining_work

U, D, L, R, W = Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT, Action.WAIT
PLAN = list(zip([R] * 5 + [L] * 5, [D, D, R, R, L, L, U, U, W, W]))


def _manual_scenario():
    layout = load_layouts()["edificio_a"]
    return Scenario(
        layout=layout,
        victims=((0, 5), (2, 2)),
        temperatures=temperature_field(layout, hotspot=(2, 4)),
        hotspot=(2, 4),
        scenario_id="edificio_a/manual",
    )


def test_trabajo_pendiente_inicial_y_progreso():
    sim = RescueSim(_manual_scenario())
    cache = DistanceCache()
    # Víctimas a 5 y 4 de la base, más acercamiento de 5 y 4 desde la base.
    assert remaining_work(sim, cache) == 18
    sim.step(R, D)
    assert remaining_work(sim, cache) == 16
    sim.step(L, U)
    assert remaining_work(sim, cache) == 18


def test_victima_transportada_cuenta_la_vuelta_a_la_base():
    sim = RescueSim(_manual_scenario())
    for a0, a1 in PLAN[:4]:
        sim.step(a0, a1)
    assert sim.robots[1].carrying == 1  # en (2, 2), a 4 de la base
    # Robot 0 en (0, 4): le falta 1 para la víctima 0, que está a 5 de la base.
    assert remaining_work(sim, DistanceCache()) == 4 + 1 + 5


def test_guia_premia_acercarse_y_castiga_alejarse():
    env = RescueEnv(load_config(), "train")
    env.reset(options={"scenario": _manual_scenario()})
    _, _, _, _, toward = env.step(encode_joint(R, D))
    _, _, _, _, away = env.step(encode_joint(L, U))
    assert toward["reward_shaping"] > 0
    assert away["reward_shaping"] < 0


def test_con_gamma_1_la_guia_total_es_el_potencial_inicial():
    config = load_config()
    config = dataclasses.replace(config, training=dataclasses.replace(config.training, gamma=1.0))
    env = RescueEnv(config, "train")
    env.reset(options={"scenario": _manual_scenario()})
    total = 0.0
    for a0, a1 in PLAN:
        _, _, _, _, info = env.step(encode_joint(a0, a1))
        total += info["reward_shaping"]
    assert info["is_success"]
    # Telescópica: Φ(éxito) − Φ(inicio) = 0 − (−0,2 × 18).
    assert total == pytest.approx(config.reward.shaping * 18)


def test_coeficiente_cero_desactiva_la_guia():
    config = load_config()
    config = dataclasses.replace(config, reward=dataclasses.replace(config.reward, shaping=0.0))
    env = RescueEnv(config, "train")
    env.reset(options={"scenario": _manual_scenario()})
    for a0, a1 in PLAN[:3]:
        _, reward, _, _, info = env.step(encode_joint(a0, a1))
        assert info["reward_shaping"] == 0.0
        assert reward == info["reward_task"]
