import dataclasses

import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env

from sar_bot.config import RewardConfig, load_config
from sar_bot.core import Action, encode_joint, load_layouts, temperature_field
from sar_bot.core.scenario import Scenario
from sar_bot.env import RescueEnv, compute_reward, observation_size, scenario_key

U, D, L, R, W = Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT, Action.WAIT


@pytest.fixture(scope="module")
def config():
    return load_config()


@pytest.fixture(scope="module")
def train_env(config):
    return RescueEnv(config, split="train")


def test_cumple_la_api_de_gymnasium(config):
    check_env(RescueEnv(config, split="train"), skip_render_check=True)


def test_espacios_de_accion_y_observacion(train_env):
    assert train_env.action_space.n == 25
    assert train_env.observation_space.shape == (observation_size((6, 6)),) == (227,)
    obs, info = train_env.reset(seed=3)
    assert obs.dtype == np.float32
    assert train_env.observation_space.contains(obs)
    assert info["step"] == 0 and info["outcome"] == "en_curso"


def test_reset_con_semilla_reproduce_el_escenario(config):
    a, b = RescueEnv(config), RescueEnv(config)
    obs_a, info_a = a.reset(seed=11)
    obs_b, info_b = b.reset(seed=11)
    assert info_a["scenario_id"] == info_b["scenario_id"]
    assert np.array_equal(obs_a, obs_b)


def test_entrenamiento_nunca_usa_escenarios_de_validacion_o_prueba(config, train_env):
    held_out = {scenario_key(s) for split in ("validation", "test") for s in RescueEnv(config, split).sampler.fixed}
    rng = np.random.default_rng(0)
    for _ in range(400):
        assert scenario_key(train_env.sampler.sample(rng)) not in held_out


def test_validacion_es_una_lista_fija_y_determinista(config):
    a, b = RescueEnv(config, "validation"), RescueEnv(config, "validation")
    assert len(a.sampler.fixed) == 3 * 50
    assert [s.scenario_id for s in a.sampler.fixed] == [s.scenario_id for s in b.sampler.fixed]
    ids = [a.reset()[1]["scenario_id"] for _ in range(3)]
    assert ids == [s.scenario_id for s in a.sampler.fixed[:3]]


def _manual_scenario():
    layout = load_layouts()["edificio_a"]
    return Scenario(
        layout=layout,
        victims=((0, 5), (2, 2)),
        temperatures=temperature_field(layout, hotspot=(2, 4)),
        hotspot=(2, 4),
        scenario_id="edificio_a/manual",
    )


def test_recompensa_y_metricas_de_una_mision_completa(config, train_env):
    obs, _ = train_env.reset(options={"scenario": _manual_scenario()})
    plan_0 = [R] * 5 + [L] * 5
    plan_1 = [D, D, R, R, L, L, U, U, W, W]
    rewards, info, terminated, truncated = [], {}, False, False
    for a0, a1 in zip(plan_0, plan_1):
        obs, reward, terminated, truncated, info = train_env.step(encode_joint(a0, a1))
        rewards.append(reward)
    rw = config.reward
    expected = 10 * rw.step + 6 * rw.damage + 2 * rw.pickup + 2 * rw.delivery + rw.success
    assert terminated and not truncated
    assert info["is_success"] is True
    assert sum(rewards) == pytest.approx(expected)
    assert info["metrics"]["return"] == pytest.approx(expected)
    assert info["metrics"]["damage_r0"] == 4.0 and info["metrics"]["damage_r1"] == 2.0
    # Paso 4: el robot 1 recoge en (2, 2) y ambos robots están en celdas a 55 °C (2 + 2 de daño).
    assert rewards[3] == pytest.approx(rw.step + 4 * rw.damage + rw.pickup)


def test_componentes_de_recompensa(train_env):
    train_env.reset(options={"scenario": _manual_scenario()})
    result = train_env.sim.step(R, D)
    custom = RewardConfig(step=-1.0, damage=0.0, pickup=0.0, delivery=0.0, success=0.0, destruction=0.0, blocked=-3.0)
    assert compute_reward(result, custom) == -1.0
    blocked = train_env.sim.step(U, W)  # el robot 0 choca con el borde superior
    assert compute_reward(blocked, custom) == -1.0 - 3.0


def test_destruccion_termina_con_penalizacion(config, train_env):
    train_env.reset(options={"scenario": _manual_scenario()})
    train_env.sim.robots[0].integrity = 2.0  # (0, 4) está a 55 °C: tasa 2
    for a0 in [R, R, R, R]:
        obs, reward, terminated, truncated, info = train_env.step(encode_joint(a0, W))
    assert terminated and not truncated
    assert info["metrics"]["outcome"] == "robot_destruido"
    assert info["is_success"] is False
    assert reward == pytest.approx(config.reward.step + 2 * config.reward.damage + config.reward.destruction)


def test_limite_de_pasos_trunca(train_env):
    train_env.reset(seed=0)
    train_env.sim.rules = dataclasses.replace(train_env.sim.rules, max_steps=3)
    flags = [train_env.step(encode_joint(W, W))[2:4] for _ in range(3)]
    assert flags == [(False, False), (False, False), (False, True)]


def test_observacion_con_una_victima_rellena_el_hueco():
    env = RescueEnv(load_config("configs/una_victima.toml"), "train")
    obs, _ = env.reset(seed=0)
    assert len(env.sim.victims) == 1
    victim_block = obs[6 * 36 + 4 : 6 * 36 + 4 + 6]
    assert victim_block.tolist() == [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    assert obs[-1] == 1.0


def test_render_ansi(config):
    env = RescueEnv(config, "validation", render_mode="ansi")
    env.reset()
    assert "paso 0/100" in env.render()
