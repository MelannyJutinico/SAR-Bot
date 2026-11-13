"""Referencias determinista y aleatoria, independientes del calor."""

from collections import deque
from itertools import combinations, permutations, product
import random

from sar_bot.core import Action, MissionState, RescueSimulation
from sar_bot.core.simulation import OFFSETS, Position, Scenario


def shortest_distance(scenario: Scenario, start: Position, goal: Position) -> int:
    """Distancia de camino por BFS, considerando paredes y límites."""
    pending = deque([(start, 0)])
    visited = {start}
    while pending:
        position, distance = pending.popleft()
        if position == goal:
            return distance
        for dx, dy in OFFSETS[:4]:
            candidate = (position[0] + dx, position[1] + dy)
            if scenario.walkable(candidate) and candidate not in visited:
                visited.add(candidate)
                pending.append((candidate, distance + 1))
    raise ValueError("No existe un camino entre las posiciones")


class RandomPolicy:
    """Acciones conjuntas uniformes; incluye esperas y movimientos inválidos."""

    def __init__(self, simulation: RescueSimulation, seed: int = 0):
        self.random = random.Random(seed)

    def act(self, state: MissionState) -> int:
        return self.random.randrange(25)


class ShortestPathPolicy:
    """Asigna víctimas y busca movimientos conjuntos mínimos sin evaluar el calor.

    Conserva cada asignación mientras la víctima siga pendiente. Planifica hasta
    los dos objetivos actuales (víctima o base), respetando las reglas del motor.
    No optimiza globalmente la misión completa y no garantiza rescates en todo mapa.
    Crear una instancia nueva al reiniciar un episodio.
    """

    def __init__(self, simulation: RescueSimulation):
        self.simulation = simulation
        self.assignments: dict[int, int] = {}
        self.last_plan_found = True

    def targets(self, state: MissionState) -> tuple[Position, Position]:
        scenario = self.simulation.scenario
        carried = {r.carrying for r in state.robots if r.carrying is not None}
        pending = set(range(2)) - set(state.rescued) - carried
        self.assignments = {
            robot_id: victim_id for robot_id, victim_id in self.assignments.items()
            if state.robots[robot_id].carrying is None and victim_id in pending
        }
        unassigned = sorted(pending - set(self.assignments.values()))
        free_robots = [i for i, r in enumerate(state.robots)
                       if r.carrying is None and i not in self.assignments]
        if unassigned:
            options = []
            for robot_ids in combinations(free_robots, len(unassigned)):
                for victim_ids in permutations(unassigned):
                    pairs = tuple(zip(robot_ids, victim_ids))
                    distance = sum(shortest_distance(scenario, state.robots[i].position,
                                                     scenario.victims[v]) for i, v in pairs)
                    options.append((distance, pairs))
            if not options:
                raise ValueError("Estado inconsistente: faltan robots para asignar víctimas")
            self.assignments.update(min(options)[1])

        return tuple(
            scenario.victims[self.assignments[i]] if i in self.assignments else scenario.base
            for i in range(2)
        )

    def act(self, state: MissionState) -> int:
        if state.outcome != "running":
            raise RuntimeError("No se puede decidir después de finalizar la misión")
        goals = self.targets(state)
        start = tuple(r.position for r in state.robots)
        # BFS en pares de posiciones: hasta 36*36 estados en mapas 6x6.
        # El primer movimiento de cada rama basta; se replantea tras cada paso real.
        queue = deque([(start, None)])
        visited = {start}
        while queue:
            positions, first_action = queue.popleft()
            if positions == goals:
                self.last_plan_found = True
                return first_action if first_action is not None else 24
            for actions in product(*(self._legal_actions(p) for p in positions)):
                joint = self.simulation.encode_actions(*actions)
                destination = self.simulation.resolve_movement(positions, joint)
                if destination not in visited:
                    visited.add(destination)
                    queue.append((destination, joint if first_action is None else first_action))

        # No se inventa una ruta: espera hasta el límite y registra el bloqueo.
        self.last_plan_found = False
        return self.simulation.encode_actions(Action.WAIT, Action.WAIT)

    def _legal_actions(self, position: Position) -> list[Action]:
        return [action for action in Action
                if self.simulation.scenario.walkable(
                    (position[0] + OFFSETS[action][0], position[1] + OFFSETS[action][1]))]
