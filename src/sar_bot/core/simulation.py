"""Motor determinista. Coordenadas (x, y), con origen arriba a la izquierda."""

from dataclasses import dataclass
from enum import IntEnum
import json
from math import isfinite
from pathlib import Path

Position = tuple[int, int]


class Action(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    WAIT = 4


OFFSETS = ((0, -1), (0, 1), (-1, 0), (1, 0), (0, 0))


def damage_rate(temperature: float) -> int:
    """Puntos de daño por unidad de tiempo simulado, no límites físicos."""
    if not isfinite(temperature):
        raise ValueError("La temperatura debe ser finita")
    if temperature < 40:
        return 0
    if temperature < 60:
        return 2
    if temperature < 80:
        return 5
    return 10


@dataclass(frozen=True)
class Scenario:
    name: str
    width: int
    height: int
    base: Position
    victims: tuple[Position, Position]
    walls: frozenset[Position]
    temperatures: tuple[tuple[float, ...], ...]
    max_steps: int = 100

    def __post_init__(self):
        if self.width < 1 or self.height < 1 or self.max_steps < 1:
            raise ValueError("Dimensiones y límite de pasos deben ser positivos")
        if len(self.victims) != 2 or len(set(self.victims)) != 2:
            raise ValueError("Se requieren dos víctimas en posiciones distintas")
        if len(self.temperatures) != self.height or any(
            len(row) != self.width for row in self.temperatures
        ):
            raise ValueError("La matriz térmica debe coincidir con el mapa")
        if any(not isfinite(t) for row in self.temperatures for t in row):
            raise ValueError("Las temperaturas deben ser finitas")
        if any(not self.in_bounds(p) for p in (self.base, *self.victims, *self.walls)):
            raise ValueError("Hay posiciones fuera del mapa")
        if self.base in self.walls or any(v in self.walls for v in self.victims):
            raise ValueError("La base y las víctimas deben estar en celdas transitables")
        if self.base in self.victims:
            raise ValueError("Las víctimas deben comenzar fuera de la base")
        if damage_rate(self.temperature_at(self.base)):
            raise ValueError("La base debe tener temperatura segura")
        reachable = {self.base}
        pending = [self.base]
        while pending:
            x, y = pending.pop()
            for dx, dy in OFFSETS[:4]:
                p = (x + dx, y + dy)
                if self.walkable(p) and p not in reachable:
                    reachable.add(p)
                    pending.append(p)
        if any(v not in reachable for v in self.victims):
            raise ValueError("Las víctimas deben estar conectadas con la base")

    def in_bounds(self, position: Position) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def walkable(self, position: Position) -> bool:
        return self.in_bounds(position) and position not in self.walls

    def temperature_at(self, position: Position) -> float:
        x, y = position
        return self.temperatures[y][x]

    @classmethod
    def load(cls, path: str | Path) -> "Scenario":
        """Carga un campo térmico estático; no modela difusión física."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        heat = data["heat"]
        ambient = float(heat["ambient"])
        peak = float(heat["peak"])
        falloff = float(heat["falloff"])
        if not all(isfinite(v) for v in (ambient, peak, falloff)):
            raise ValueError("Los parámetros térmicos deben ser finitos")
        if peak < ambient or falloff < 0:
            raise ValueError("Se requiere pico >= ambiente y caída >= 0")
        fx, fy = heat["focus"]
        if not (0 <= fx < data["width"] and 0 <= fy < data["height"]):
            raise ValueError("El foco debe estar dentro del mapa")
        temperatures = tuple(
            tuple(max(ambient, peak - falloff * (abs(x - fx) + abs(y - fy)))
                  for x in range(data["width"]))
            for y in range(data["height"])
        )
        return cls(
            name=data["name"], width=data["width"], height=data["height"],
            base=tuple(data["base"]),
            victims=tuple(tuple(v) for v in data["victims"]),
            walls=frozenset(tuple(w) for w in data["walls"]),
            temperatures=temperatures, max_steps=data.get("max_steps", 100),
        )


@dataclass(frozen=True)
class Robot:
    position: Position
    integrity: int = 100
    carrying: int | None = None
    damage: int = 0


@dataclass(frozen=True)
class MissionState:
    robots: tuple[Robot, Robot]
    rescued: frozenset[int] = frozenset()
    steps: int = 0
    outcome: str = "running"

    @property
    def terminated(self) -> bool:
        return self.outcome in ("success", "destroyed")

    @property
    def truncated(self) -> bool:
        return self.outcome == "time_limit"


class RescueSimulation:
    """Una llamada a step avanza el reloj una vez para ambos robots."""

    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self.reset()

    def reset(self) -> MissionState:
        self.state = MissionState((Robot(self.scenario.base), Robot(self.scenario.base)))
        return self.state

    @staticmethod
    def encode_actions(first: Action, second: Action) -> int:
        return 5 * Action(first).value + Action(second).value

    @staticmethod
    def decode_action(joint_action: int) -> tuple[Action, Action]:
        if type(joint_action) is not int or not 0 <= joint_action < 25:
            raise ValueError("La acción conjunta debe ser un entero entre 0 y 24")
        first, second = divmod(joint_action, 5)
        return Action(first), Action(second)

    def resolve_movement(
        self, positions: tuple[Position, Position], joint_action: int
    ) -> tuple[Position, Position]:
        """Resuelve un movimiento hipotético sin avanzar tiempo ni alterar el estado.

        El planificador y step comparten estas reglas de colisión.
        """
        actions = self.decode_action(joint_action)
        old = positions
        destinations = []
        for position, action in zip(old, actions):
            dx, dy = OFFSETS[action]
            candidate = (position[0] + dx, position[1] + dy)
            destinations.append(candidate if self.scenario.walkable(candidate) else position)

        same_cell = destinations[0] == destinations[1] != self.scenario.base
        swap = old[0] != old[1] and destinations == [old[1], old[0]]
        if same_cell or swap:
            destinations = list(old)

        return tuple(destinations)

    def step(self, joint_action: int) -> MissionState:
        if self.state.outcome != "running":
            raise RuntimeError("La misión terminó; ejecutar reset antes de continuar")
        destinations = self.resolve_movement(
            tuple(robot.position for robot in self.state.robots), joint_action
        )

        robots = []
        for robot, destination in zip(self.state.robots, destinations):
            exposure = damage_rate(self.scenario.temperature_at(destination))
            actual_damage = min(robot.integrity, exposure)
            robots.append(Robot(destination, robot.integrity - actual_damage,
                                robot.carrying, robot.damage + actual_damage))

        steps = self.state.steps + 1
        rescued = set(self.state.rescued)
        if any(robot.integrity == 0 for robot in robots):
            outcome = "destroyed"
        else:
            assigned = rescued | {r.carrying for r in robots if r.carrying is not None}
            for i, robot in enumerate(robots):
                carrying = robot.carrying
                if carrying is None:
                    for victim_id, position in enumerate(self.scenario.victims):
                        if victim_id not in assigned and robot.position == position:
                            carrying = victim_id
                            assigned.add(victim_id)
                            break
                if carrying is not None and robot.position == self.scenario.base:
                    rescued.add(carrying)
                    carrying = None
                robots[i] = Robot(robot.position, robot.integrity, carrying, robot.damage)
            outcome = "success" if len(rescued) == 2 else "running"
            if outcome == "running" and steps >= self.scenario.max_steps:
                outcome = "time_limit"

        self.state = MissionState(tuple(robots), frozenset(rescued), steps, outcome)
        return self.state

    def snapshot(self) -> dict:
        """Datos JSON para futuras interfaces y evaluación; sin referencias mutables."""
        return {
            "scenario": self.scenario.name,
            "steps": self.state.steps,
            "outcome": self.state.outcome,
            "rescued": sorted(self.state.rescued),
            "robots": [
                {"position": list(r.position), "integrity": r.integrity,
                 "carrying": r.carrying, "damage": r.damage,
                 "temperature": self.scenario.temperature_at(r.position)}
                for r in self.state.robots
            ],
        }
