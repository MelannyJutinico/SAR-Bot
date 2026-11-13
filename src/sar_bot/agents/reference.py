"""Referencias de navegación, riesgo térmico y acciones aleatorias."""

from collections import deque
from itertools import combinations, permutations, product
from heapq import heappop, heappush
from math import isfinite
import random

from sar_bot.core import Action, MissionState, RescueSimulation, damage_rate
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
        self._planned_goals = None
        self._plan = deque()
        self._distances = {}
        self._legal_cache = {}
        self.damage_weight = 0.0
        self.replans = 0
        self.total_expanded = 0

    def targets(self, state: MissionState) -> tuple[Position, Position]:
        scenario = self.simulation.scenario
        carried = {r.carrying for r in state.robots if r.carrying is not None}
        pending = set(range(scenario.victim_count)) - set(state.rescued) - carried
        self.assignments = {
            robot_id: victim_id for robot_id, victim_id in self.assignments.items()
            if state.robots[robot_id].carrying is None and victim_id in pending
        }
        unassigned = sorted(pending - set(self.assignments.values()))
        free_robots = [i for i, r in enumerate(state.robots)
                       if r.carrying is None and i not in self.assignments]
        count = min(len(unassigned), len(free_robots))
        if count:
            options = []
            for robot_ids in combinations(free_robots, count):
                for victim_ids in permutations(unassigned, count):
                    pairs = tuple(zip(robot_ids, victim_ids))
                    distance = sum(self._distance_to(scenario.victims[v])[state.robots[i].position]
                                   for i, v in pairs)
                    options.append((distance, pairs))
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
        if self._planned_goals == goals and self._plan and self._plan[0][0] == start:
            self.last_plan_found = True
            return self._plan.popleft()[1]
        self._plan.clear()
        self._planned_goals = goals
        self.replans += 1
        maps = tuple(self._distance_to(goal) for goal in goals)

        def heuristic(positions):
            return max(maps[i][position] for i, position in enumerate(positions))

        # A* conjunto: la distancia máxima individual es una cota inferior de pasos.
        # El costo térmico es no negativo; la misma cota sirve para ambas referencias.
        queue = [(heuristic(start), 0, 0.0, start)]
        best_cost, parents = {start: 0.0}, {start: None}
        counter = 0
        while queue:
            _, _, cost, positions = heappop(queue)
            if cost != best_cost[positions]:
                continue
            self.total_expanded += 1
            if positions == goals:
                plan = []
                current = positions
                while parents[current] is not None:
                    previous, joint = parents[current]
                    plan.append((previous, joint))
                    current = previous
                self._plan = deque(reversed(plan))
                self.last_plan_found = True
                return self._plan.popleft()[1] if self._plan else 24
            for actions in product(*(self._legal_actions(p) for p in positions)):
                joint = self.simulation.encode_actions(*actions)
                destination = self.simulation.resolve_movement(positions, joint)
                exposure = (sum(damage_rate(self.simulation.scenario.temperature_at(p))
                                for p in destination) if self.damage_weight else 0)
                next_cost = cost + 1 + self.damage_weight * exposure
                if next_cost < best_cost.get(destination, float("inf")):
                    best_cost[destination] = next_cost
                    parents[destination] = positions, joint
                    counter += 1
                    heappush(queue, (next_cost + heuristic(destination), counter, next_cost, destination))

        # No se inventa una ruta: espera hasta el límite y registra el bloqueo.
        self.last_plan_found = False
        return self.simulation.encode_actions(Action.WAIT, Action.WAIT)

    def _legal_actions(self, position: Position) -> list[Action]:
        if position not in self._legal_cache:
            self._legal_cache[position] = [action for action in Action
                if self.simulation.scenario.walkable((position[0] + OFFSETS[action][0],
                                                     position[1] + OFFSETS[action][1]))]
        return self._legal_cache[position]

    def _distance_to(self, goal):
        if goal not in self._distances:
            distances = {goal: 0}
            queue = deque([goal])
            while queue:
                position = queue.popleft()
                for dx, dy in OFFSETS[:4]:
                    neighbor = (position[0] + dx, position[1] + dy)
                    if self.simulation.scenario.walkable(neighbor) and neighbor not in distances:
                        distances[neighbor] = distances[position] + 1
                        queue.append(neighbor)
            self._distances[goal] = distances
        return self._distances[goal]


class ThermalPathPolicy(ShortestPathPolicy):
    """Referencia A* térmica: minimiza pasos + peso × exposición prevista.

    Conserva la asignación de la referencia geométrica. No es aprendizaje ni
    un óptimo global de toda la misión; replanifica para los objetivos actuales.
    """

    def __init__(self, simulation: RescueSimulation, damage_weight: float = 2.0):
        super().__init__(simulation)
        if not isfinite(damage_weight) or damage_weight < 0:
            raise ValueError("El peso del daño debe ser finito y no negativo")
        self.damage_weight = damage_weight

