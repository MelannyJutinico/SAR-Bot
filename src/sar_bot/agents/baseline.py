"""Estrategia de referencia programada (docs/CONTEXTO.md §9).

Asigna víctimas distintas por distancia de camino y sigue rutas más cortas
que ignoran el calor, con las mismas reglas de colisión y tiempo que el
agente aprendido.

Reglas, en cada paso global:

1. Asignación. Al inicio y cada vez que cambia el estado de las víctimas,
   cada robot vacío recibe una víctima esperando distinta, minimizando la
   suma de distancias de camino (BFS). Si hay más robots vacíos que
   víctimas, el sobrante vuelve a la base y espera allí.
2. Objetivo. Un robot cargado va a la base; uno vacío, a su víctima.
3. Propuesta. Cada robot propone el movimiento que más reduce su distancia
   de camino al objetivo (empates: arriba, abajo, izquierda, derecha). En el
   objetivo, espera.
4. Bloqueos. Si las propuestas chocan según el motor (misma celda o
   intercambio), el robot con prioridad mantiene la suya. Prioridad: el que
   transporta víctima; si ambos o ninguno, el más cercano a su objetivo; si
   empatan, el robot 0. El otro elige, entre sus cinco acciones, la que no
   bloquea al prioritario y deja menor distancia a su propio objetivo; ante
   empate prefiere esperar. Así puede apartarse en un pasillo.
5. Si ninguna alternativa evita el bloqueo, ambos mantienen su propuesta y
   el motor los bloquea en ese paso.
"""

from __future__ import annotations

import itertools

import numpy as np

from sar_bot.core.actions import Action, encode_joint, target_cell
from sar_bot.core.engine import RescueSim, VictimStatus, resolve_moves
from sar_bot.core.grid import Layout, Pos

_MOVES = (Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT)
_YIELD_ORDER = (Action.WAIT, *_MOVES)


class ShortestPathBaseline:
    name = "referencia"

    def __init__(self) -> None:
        self._layout: Layout | None = None
        self._distances: dict[Pos, dict[Pos, int]] = {}
        self._assignment: dict[int, int] = {}
        self._victim_signature: tuple | None = None

    def reset(self, sim: RescueSim) -> None:
        if sim.layout is not self._layout:
            self._layout = sim.layout
            self._distances = {}
        self._assignment = {}
        self._victim_signature = None

    def _dist(self, target: Pos) -> dict[Pos, int]:
        if target not in self._distances:
            self._distances[target] = self._layout.distances_from(target)
        return self._distances[target]

    def _update_assignment(self, sim: RescueSim) -> None:
        signature = tuple((v.status, v.carrier) for v in sim.victims)
        if signature == self._victim_signature:
            return
        self._victim_signature = signature
        empty = [i for i, robot in enumerate(sim.robots) if robot.carrying is None]
        waiting = [k for k, victim in enumerate(sim.victims) if victim.status is VictimStatus.WAITING]
        m = min(len(empty), len(waiting))
        best: dict[int, int] = {}
        best_cost = float("inf")
        for robots in itertools.combinations(empty, m):
            for victims in itertools.permutations(waiting, m):
                cost = sum(
                    self._dist(sim.victims[k].origin)[sim.robots[i].pos] for i, k in zip(robots, victims)
                )
                if cost < best_cost:
                    best_cost, best = cost, dict(zip(robots, victims))
        self._assignment = best

    def targets(self, sim: RescueSim) -> list[Pos]:
        """Objetivo actual de cada robot según las reglas 1 y 2."""
        self._update_assignment(sim)
        base = sim.layout.base
        result = []
        for i, robot in enumerate(sim.robots):
            if robot.carrying is None and i in self._assignment:
                result.append(sim.victims[self._assignment[i]].origin)
            else:
                result.append(base)
        return result

    def _greedy(self, pos: Pos, target: Pos) -> Action:
        if pos == target:
            return Action.WAIT
        dist = self._dist(target)
        best, best_d = Action.WAIT, dist[pos]
        for action in _MOVES:
            nxt = target_cell(pos, action)
            if self._layout.is_free(nxt) and dist[nxt] < best_d:
                best, best_d = action, dist[nxt]
        return best

    def _priority(self, sim: RescueSim, targets: list[Pos]) -> int:
        carrying = [robot.carrying is not None for robot in sim.robots]
        if carrying[0] != carrying[1]:
            return 0 if carrying[0] else 1
        d0 = self._dist(targets[0])[sim.robots[0].pos]
        d1 = self._dist(targets[1])[sim.robots[1].pos]
        return 0 if d0 <= d1 else 1

    def act(self, observation: np.ndarray | None, sim: RescueSim) -> int:
        if sim.layout is not self._layout or sim.step_count == 0:
            self.reset(sim)
        targets = self.targets(sim)
        positions = sim.positions
        proposal = [self._greedy(positions[i], targets[i]) for i in range(2)]
        moves = resolve_moves(self._layout, positions, tuple(proposal))
        if not any(moves.blocked_by_robot):
            return encode_joint(*proposal)

        first = self._priority(sim, targets)
        other = 1 - first
        other_dist = self._dist(targets[other])
        best_action, best_d = None, None
        for action in _YIELD_ORDER:
            candidate = list(proposal)
            candidate[other] = action
            res = resolve_moves(self._layout, positions, tuple(candidate))
            if res.blocked_by_robot[first] or res.blocked_by_wall[other]:
                continue
            d = other_dist[res.positions[other]]
            if best_d is None or d < best_d:
                best_action, best_d = action, d
        if best_action is not None:
            proposal[other] = best_action
        return encode_joint(*proposal)
