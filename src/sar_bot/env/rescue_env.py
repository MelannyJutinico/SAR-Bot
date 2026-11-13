"""Observación completa y recompensa sobre el mismo motor de simulación."""

from collections import deque
from dataclasses import dataclass
from itertools import permutations, product
from math import isfinite

import gymnasium as gym
from gymnasium import spaces
import numpy as np

from sar_bot.core import MissionState, RescueSimulation, Scenario
from sar_bot.core.simulation import OFFSETS


@dataclass(frozen=True)
class RewardConfig:
    step: float = -1.0
    pickup: float = 5.0
    delivery: float = 50.0
    success: float = 100.0
    destruction: float = -100.0
    timeout: float = -20.0
    damage: float = -1.0
    shaping: float = 2.0
    gamma: float = 0.99

    def __post_init__(self):
        if not all(isfinite(value) for value in vars(self).values()):
            raise ValueError("Las recompensas deben ser finitas")
        if not 0 < self.gamma <= 1:
            raise ValueError("gamma debe estar en (0, 1]")


class RescueEnv(gym.Env):
    """Discrete(25), observación numérica completa, muestreo de escenarios al reset.

    No renderiza: la interfaz debe consumir simulation.snapshot(). Escenarios de
    un mismo entorno deben compartir dimensiones para mantener la observación fija.
    """

    metadata = {"render_modes": []}

    def __init__(self, scenarios: list[Scenario], rewards: RewardConfig | None = None):
        super().__init__()
        if not scenarios:
            raise ValueError("Se requiere al menos un escenario")
        self.scenarios = tuple(scenarios)
        self.width, self.height = scenarios[0].width, scenarios[0].height
        if any((s.width, s.height) != (self.width, self.height) for s in scenarios):
            raise ValueError("Todos los escenarios deben compartir dimensiones")
        self.rewards = rewards or RewardConfig()
        self.action_space = spaces.Discrete(25)
        self.observation_space = spaces.Box(
            0.0, 1.0, shape=(2 * self.width * self.height + 25,), dtype=np.float32
        )
        self._distances = [self._compute_distances(s) for s in scenarios]
        self.scenario_index = 0
        self.simulation = RescueSimulation(scenarios[0])
        self._needs_reset = True

    @staticmethod
    def _compute_distances(scenario):
        distances = {}
        for y in range(scenario.height):
            for x in range(scenario.width):
                start = (x, y)
                if not scenario.walkable(start):
                    continue
                queue = deque([(start, 0)])
                visited = {start}
                while queue:
                    position, distance = queue.popleft()
                    distances[start, position] = distance
                    for dx, dy in OFFSETS[:4]:
                        neighbor = (position[0] + dx, position[1] + dy)
                        if scenario.walkable(neighbor) and neighbor not in visited:
                            visited.add(neighbor)
                            queue.append((neighbor, distance + 1))
        return distances

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if options and "scenario_index" in options:
            index = options["scenario_index"]
            if type(index) is not int or not 0 <= index < len(self.scenarios):
                raise ValueError("scenario_index fuera de rango")
        else:
            index = int(self.np_random.integers(len(self.scenarios)))
        self.scenario_index = index
        self.simulation = RescueSimulation(self.scenarios[index])
        self._needs_reset = False
        return self.observation(), self._info()

    def observation(self):
        """Vector normalizado: paredes, calor, posiciones, salud, carga, víctimas, reloj."""
        scenario, state = self.simulation.scenario, self.simulation.state
        values = [float((x, y) in scenario.walls)
                  for y in range(self.height) for x in range(self.width)]
        values.extend(float(np.clip(t, 0, 200)) / 200
                      for row in scenario.temperatures for t in row)
        for x, y in (scenario.base, *scenario.victims, *(r.position for r in state.robots)):
            values.extend((x / max(1, self.width - 1), y / max(1, self.height - 1)))
        values.extend(r.integrity / 100 for r in state.robots)
        for robot in state.robots:
            slot = 0 if robot.carrying is None else robot.carrying + 1
            values.extend(float(i == slot) for i in range(3))
        for victim_id in range(2):
            status = (2 if victim_id in state.rescued else
                      1 if any(r.carrying == victim_id for r in state.robots) else 0)
            values.extend(float(i == status) for i in range(3))
        values.append(state.steps / scenario.max_steps)
        return np.asarray(values, dtype=np.float32)

    def _potential(self, state: MissionState):
        if state.terminated:
            return 0.0
        scenario = self.simulation.scenario
        distances = self._distances[self.scenario_index]
        carried = {r.carrying for r in state.robots if r.carrying is not None}
        pending = sorted(set(range(2)) - set(state.rescued) - carried)
        best = float("inf")
        # Heurística de trabajo restante: distancias sin colisiones ni calor.
        for owners in product(range(2), repeat=len(pending)):
            total = 0
            for robot_id, robot in enumerate(state.robots):
                position = robot.position
                if robot.carrying is not None:
                    total += distances[position, scenario.base]
                    position = scenario.base
                assigned = [v for v, owner in zip(pending, owners) if owner == robot_id]
                route_costs = []
                for order in permutations(assigned):
                    cost, current = 0, position
                    for victim_id in order:
                        victim = scenario.victims[victim_id]
                        cost += distances[current, victim] + distances[victim, scenario.base]
                        current = scenario.base
                    route_costs.append(cost)
                total += min(route_costs)
            best = min(best, total)
        return -float(best)

    def _info(self):
        return {**self.simulation.snapshot(), "is_success": self.simulation.state.outcome == "success",
                "scenario_index": self.scenario_index}

    def step(self, action):
        if self._needs_reset:
            raise RuntimeError("Ejecutar reset antes de step")
        if isinstance(action, (bool, np.bool_)) or not self.action_space.contains(action):
            raise ValueError("La acción debe ser un entero entre 0 y 24")
        before = self.simulation.state
        potential_before = self._potential(before)
        state = self.simulation.step(int(action))
        picked_before = set(before.rescued) | {r.carrying for r in before.robots if r.carrying is not None}
        picked_after = set(state.rescued) | {r.carrying for r in state.robots if r.carrying is not None}
        damage = sum(r.damage for r in state.robots) - sum(r.damage for r in before.robots)
        r = self.rewards
        terms = {
            "step": r.step,
            "pickup": r.pickup * len(picked_after - picked_before),
            "delivery": r.delivery * len(state.rescued - before.rescued),
            "damage": r.damage * damage,
            "terminal": (r.success if state.outcome == "success" else
                         r.destruction if state.outcome == "destroyed" else
                         r.timeout if state.truncated else 0.0),
            "shaping": r.shaping * (r.gamma * self._potential(state) - potential_before),
        }
        self._needs_reset = state.terminated or state.truncated
        info = {**self._info(), "reward_terms": terms}
        return self.observation(), float(sum(terms.values())), state.terminated, state.truncated, info
