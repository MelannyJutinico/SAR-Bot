"""Observación completa y recompensa sobre el mismo motor de simulación."""

from collections import deque
from dataclasses import dataclass
from itertools import product
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
    potential_bound: float = 0.0

    def __post_init__(self):
        if not all(isfinite(value) for value in vars(self).values()):
            raise ValueError("Las recompensas deben ser finitas")
        if not 0 < self.gamma <= 1:
            raise ValueError("gamma debe estar en (0, 1]")
        if self.potential_bound < 0:
            raise ValueError("El límite del potencial debe ser no negativo")


class RescueEnv(gym.Env):
    """Discrete(25), observación numérica completa, muestreo de escenarios al reset.

    No renderiza: la interfaz debe consumir simulation.snapshot(). Escenarios de
    un mismo entorno deben compartir dimensiones para mantener la observación fija.
    """

    metadata = {"render_modes": []}

    def __init__(self, scenarios: list[Scenario], rewards: RewardConfig | None = None,
                 observation_mode: str = "full"):
        super().__init__()
        if not scenarios:
            raise ValueError("Se requiere al menos un escenario")
        self.scenarios = tuple(scenarios)
        self.width, self.height = scenarios[0].width, scenarios[0].height
        self.victim_count = scenarios[0].victim_count
        if any((s.width, s.height, s.victim_count) != (self.width, self.height, self.victim_count)
               for s in scenarios):
            raise ValueError("Los escenarios de un perfil deben compartir dimensiones y cantidad de personas")
        self.rewards = rewards or RewardConfig()
        if observation_mode not in ("full", "sensors"):
            raise ValueError("observation_mode debe ser full o sensors")
        self.observation_mode = observation_mode
        self.action_space = spaces.Discrete(25)
        self.observation_space = spaces.Box(
            0.0, 1.0,
            shape=(self.observation_size(self.width, self.height, self.victim_count, observation_mode),),
            dtype=np.float32
        )
        self._distances = [self._compute_distances(s) for s in scenarios]
        # Toda entrega con capacidad uno cuesta a lo sumo dos recorridos simples
        # por persona. Escala fija por edificio: no altera el potencial entre pasos.
        self._potential_scales = [min(1.0, self.rewards.potential_bound / max(
            1, 2 * self.victim_count * (s.width * s.height - len(s.walls) - 1)))
            if self.rewards.potential_bound else 1.0 for s in scenarios]
        self.scenario_index = 0
        self.simulation = RescueSimulation(scenarios[0])
        self._needs_reset = True

    @staticmethod
    def observation_size(width, height, victims, mode):
        return 2 * width * height + 11 + 7 * victims + (40 + 10 * victims if mode == "sensors" else 0)

    @property
    def profile(self):
        return {"schema_version": 2, "width": self.width, "height": self.height,
                "victims": self.victim_count, "mode": self.observation_mode,
                "observation_size": self.observation_space.shape[0], "actions": 25}

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
        scenario = self.scenarios[index]
        if options and "victim_positions" in options:
            scenario = scenario.with_victims(options["victim_positions"])
            if scenario.victim_count != self.victim_count:
                raise ValueError("La cantidad de personas editadas debe coincidir con el perfil")
        self.scenario_index = index
        self.simulation = RescueSimulation(scenario)
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
            values.extend(float(i == slot) for i in range(self.victim_count + 1))
        for victim_id in range(self.victim_count):
            status = (2 if victim_id in state.rescued else
                      1 if any(r.carrying == victim_id for r in state.robots) else 0)
            values.extend(float(i == status) for i in range(3))
        values.append(state.steps / scenario.max_steps)
        if self.observation_mode == "sensors":
            # Datos locales explícitos: la MLP no necesita aprender a indexar el
            # mapa a partir de coordenadas para reconocer paredes o calor cercano.
            distances = self._distances[self.scenario_index]
            for robot_id, robot in enumerate(state.robots):
                for dx, dy in OFFSETS:
                    candidate = (robot.position[0] + dx, robot.position[1] + dy)
                    legal = scenario.walkable(candidate)
                    destination = candidate if legal else robot.position
                    occupied = (destination == state.robots[1 - robot_id].position
                                and destination != scenario.base)
                    values.extend((float(legal), float(occupied),
                                   float(np.clip(scenario.temperature_at(destination), 0, 200)) / 200))
                    for goal in (scenario.base, *scenario.victims):
                        values.append(distances.get((destination, goal), self.width * self.height)
                                      / (self.width * self.height))
        return np.asarray(values, dtype=np.float32)

    def _potential(self, state: MissionState):
        if state.terminated:
            return 0.0
        scenario = self.simulation.scenario
        distances = self._distances[self.scenario_index]
        carried = {r.carrying for r in state.robots if r.carrying is not None}
        pending = sorted(set(range(self.victim_count)) - set(state.rescued) - carried)
        # Capacidad uno: tras la primera entrega todos los viajes restantes salen
        # de la base. Basta elegir la primera persona de cada robot, sin N! rutas.
        starts = [scenario.base if r.carrying is not None else r.position for r in state.robots]
        baseline = sum(distances[r.position, scenario.base] for r in state.robots if r.carrying is not None)
        baseline += 2 * sum(distances[scenario.base, scenario.victims[v]] for v in pending)
        best = float("inf")
        for first in product([None, *pending], repeat=2):
            if pending and first == (None, None):
                continue
            if first[0] is not None and first[0] == first[1]:
                continue
            total = baseline
            for i, victim_id in enumerate(first):
                if victim_id is not None:
                    victim = scenario.victims[victim_id]
                    total += distances[starts[i], victim] - distances[scenario.base, victim]
            best = min(best, total)
        return -float(best) * self._potential_scales[self.scenario_index]

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
