"""Recompensa de guía basada en potencial (Ng, Harada y Russell, 1999).

Se suma ``F = γ·Φ(s') − Φ(s)`` a la recompensa de la tarea, con
``Φ(s) = −coeficiente × trabajo_pendiente(s)``. Una guía de esta forma no
cambia qué política es óptima entre las misiones exitosas: solo da una señal
densa de progreso para que el aprendizaje no dependa de encontrar rescates
completos por azar.

``trabajo_pendiente`` es una suma de distancias de camino (BFS, sin calor):

- víctima transportada: distancia del robot que la lleva a la base;
- víctima esperando: distancia de la víctima a la base, más la distancia de
  acercamiento del robot vacío asignado (asignación distinta que minimiza la
  suma). Si no queda robot vacío, se cuenta el viaje desde la base;
- víctima rescatada: 0.

En el estado de éxito el potencial vale 0. En una destrucción el potencial
final es negativo, lo que añade una penalización proporcional al trabajo
pendiente; nunca premia destruirse.
"""

from __future__ import annotations

import itertools

from sar_bot.core.engine import RescueSim, VictimStatus
from sar_bot.core.grid import Layout, Pos


class DistanceCache:
    """Distancias de camino desde cada objetivo, por plano."""

    def __init__(self) -> None:
        self._cache: dict[tuple[int, Pos], dict[Pos, int]] = {}

    def from_target(self, layout: Layout, target: Pos) -> dict[Pos, int]:
        key = (id(layout), target)
        if key not in self._cache:
            self._cache[key] = layout.distances_from(target)
        return self._cache[key]


def remaining_work(sim: RescueSim, distances: DistanceCache) -> float:
    layout = sim.layout
    to_base = distances.from_target(layout, layout.base)
    total = 0.0
    for robot in sim.robots:
        if robot.carrying is not None:
            total += to_base[robot.pos]

    waiting = [v.origin for v in sim.victims if v.status is VictimStatus.WAITING]
    total += sum(to_base[v] for v in waiting)
    empty = [robot.pos for robot in sim.robots if robot.carrying is None]
    m = min(len(empty), len(waiting))
    best = float("inf")
    for robots in itertools.permutations(empty, m):
        for victims in itertools.combinations(waiting, m):
            approach = sum(distances.from_target(layout, v)[r] for r, v in zip(robots, victims))
            unserved = sum(to_base[v] for v in waiting if v not in victims)
            best = min(best, approach + unserved)
    return total + (best if waiting else 0.0)


def potential(sim: RescueSim, distances: DistanceCache, coefficient: float) -> float:
    if coefficient == 0.0:
        return 0.0
    return -coefficient * remaining_work(sim, distances)
