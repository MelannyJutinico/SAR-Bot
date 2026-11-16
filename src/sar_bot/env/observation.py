"""Observación de tamaño fijo con valores en [0, 1].

Vector ``float32`` que concatena seis capas del mapa (alto × ancho cada una)
y un bloque de escalares:

Capas
    0. obstáculos
    1. calor: tasa de daño de la celda dividida por la tasa máxima
    2. base
    3. posición del robot 0
    4. posición del robot 1
    5. víctimas esperando

Escalares
    - integridad de cada robot como fracción de la inicial (2)
    - carga de cada robot, 0 o 1 (2)
    - estado de cada víctima en one-hot (esperando, transportada, rescatada);
      ceros si esa víctima no existe en el escenario (3 × MAX_VICTIMS)
    - fracción de pasos restantes (1)

Para un plano de 6 × 6 el tamaño es 6·36 + 2 + 2 + 6 + 1 = 227.
"""

from __future__ import annotations

import numpy as np

from sar_bot.config import MAX_VICTIMS
from sar_bot.core.actions import N_ROBOTS
from sar_bot.core.engine import RescueSim, VictimStatus
from sar_bot.core.rules import RulesConfig, damage_rate
from sar_bot.core.scenario import Scenario

N_LAYERS = 6
VICTIM_STATES = (VictimStatus.WAITING, VictimStatus.CARRIED, VictimStatus.RESCUED)


def observation_size(shape: tuple[int, int], max_victims: int = MAX_VICTIMS) -> int:
    height, width = shape
    return N_LAYERS * height * width + 2 * N_ROBOTS + len(VICTIM_STATES) * max_victims + 1


def heat_layer(scenario: Scenario, rules: RulesConfig) -> np.ndarray:
    """Tasa de daño por celda normalizada por la tasa máxima de las franjas."""
    max_rate = max((rate for _, rate in rules.damage_bands), default=0.0)
    if max_rate <= 0:
        return np.zeros(scenario.layout.shape, dtype=np.float32)
    rates = np.vectorize(lambda t: damage_rate(t, rules.damage_bands))(scenario.temperatures)
    return (rates / max_rate).astype(np.float32)


def build_observation(sim: RescueSim, heat: np.ndarray, max_victims: int = MAX_VICTIMS) -> np.ndarray:
    if len(sim.victims) > max_victims:
        raise ValueError(f"la observación admite hasta {max_victims} víctimas")
    layout = sim.layout
    layers = np.zeros((N_LAYERS, *layout.shape), dtype=np.float32)
    layers[0] = layout.walls
    layers[1] = heat
    layers[2][layout.base] = 1.0
    for i, robot in enumerate(sim.robots):
        layers[3 + i][robot.pos] = 1.0
    for victim in sim.victims:
        if victim.status is VictimStatus.WAITING:
            layers[5][victim.origin] = 1.0

    initial = sim.rules.initial_integrity
    scalars: list[float] = [robot.integrity / initial for robot in sim.robots]
    scalars += [float(robot.carrying is not None) for robot in sim.robots]
    for slot in range(max_victims):
        status = sim.victims[slot].status if slot < len(sim.victims) else None
        scalars += [float(status is state) for state in VICTIM_STATES]
    scalars.append((sim.rules.max_steps - sim.step_count) / sim.rules.max_steps)

    return np.concatenate([layers.ravel(), np.asarray(scalars, dtype=np.float32)])
