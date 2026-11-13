"""Motor determinista. Coordenadas (x, y), con origen arriba a la izquierda."""

from dataclasses import dataclass, replace
from enum import IntEnum
import json
from math import isfinite
from pathlib import Path
from hashlib import sha256
from numbers import Real
from functools import cached_property

Position = tuple[int, int]


class Action(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    WAIT = 4


OFFSETS = ((0, -1), (0, 1), (-1, 0), (1, 0), (0, 0))


def _position(value, label="posición") -> Position:
    if not isinstance(value, (tuple, list)) or len(value) != 2 or any(type(v) is not int for v in value):
        raise ValueError(f"{label}: se requieren dos coordenadas enteras")
    return tuple(value)


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"{label} debe ser un número finito")
    return float(value)


@dataclass(frozen=True)
class HeatSource:
    focus: Position
    peak: float
    falloff: float

    def __post_init__(self):
        object.__setattr__(self, "focus", _position(self.focus, "Foco térmico"))
        object.__setattr__(self, "peak", _number(self.peak, "Pico térmico"))
        object.__setattr__(self, "falloff", _number(self.falloff, "Caída térmica"))
        if self.falloff < 0:
            raise ValueError("La caída térmica debe ser no negativa")

    def to_dict(self):
        return {"focus": list(self.focus), "peak": self.peak, "falloff": self.falloff}


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
    victims: tuple[Position, ...]
    walls: frozenset[Position]
    temperatures: tuple[tuple[float, ...], ...]
    max_steps: int = 100
    heat_sources: tuple[HeatSource, ...] = ()
    ambient_temperature: float = 25.0

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("El escenario necesita un nombre")
        if any(type(v) is not int or v < 1 for v in (self.width, self.height, self.max_steps)):
            raise ValueError("Dimensiones y límite de pasos deben ser positivos")
        object.__setattr__(self, "base", _position(self.base, "Base"))
        object.__setattr__(self, "victims", tuple(_position(p, "Persona") for p in self.victims))
        object.__setattr__(self, "walls", frozenset(_position(p, "Obstáculo") for p in self.walls))
        object.__setattr__(self, "heat_sources", tuple(self.heat_sources))
        object.__setattr__(self, "ambient_temperature", _number(self.ambient_temperature, "Ambiente"))
        if not self.victims or len(set(self.victims)) != len(self.victims):
            raise ValueError("Se requiere al menos una persona y posiciones distintas")
        if len(self.temperatures) != self.height or any(
            len(row) != self.width for row in self.temperatures
        ):
            raise ValueError("La matriz térmica debe coincidir con el mapa")
        object.__setattr__(self, "temperatures", tuple(
            tuple(_number(t, "Temperatura") for t in row) for row in self.temperatures))
        if any(not self.in_bounds(p) for p in (self.base, *self.victims, *self.walls)):
            raise ValueError("Hay posiciones fuera del mapa")
        if self.base in self.walls or any(v in self.walls for v in self.victims):
            raise ValueError("La base y las víctimas deben estar en celdas transitables")
        if self.base in self.victims:
            raise ValueError("Las víctimas deben comenzar fuera de la base")
        if damage_rate(self.temperature_at(self.base)):
            raise ValueError("La base debe tener temperatura segura")
        for source in self.heat_sources:
            if not isinstance(source, HeatSource) or not self.in_bounds(source.focus):
                raise ValueError("Los focos deben ser HeatSource dentro del mapa")
            if source.peak < self.ambient_temperature:
                raise ValueError("El pico térmico debe ser mayor o igual al ambiente")
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
        """Acepta el formato histórico y el formato V2 con varios focos o matriz explícita."""
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def from_dict(cls, data: dict) -> "Scenario":
        if not isinstance(data, dict):
            raise ValueError("El escenario debe ser un objeto JSON")
        try:
            version = data.get("schema_version", 1)
            if type(version) is not int or version not in (1, 2):
                raise ValueError("Versión de escenario no compatible")
            width, height = data["width"], data["height"]
            if any(type(v) is not int or v < 1 for v in (width, height)):
                raise ValueError("Dimensiones enteras positivas requeridas")
            if "temperatures" in data:
                if "heat" in data:
                    raise ValueError("Usar heat o temperatures, no ambos")
                ambient = _number(data.get("ambient_temperature", 25), "Ambiente")
                sources = tuple(HeatSource(**s) for s in data.get("heat_sources", []))
                temperatures = data["temperatures"]
            else:
                heat = data["heat"]
                ambient = _number(heat["ambient"], "Ambiente")
                if heat.get("combine", "max") != "max":
                    raise ValueError("La combinación térmica soportada es max")
                if "sources" in heat and "focus" in heat:
                    raise ValueError("No mezclar foco histórico y lista de focos")
                definitions = (heat["sources"] if "sources" in heat else
                               [{key: heat[key] for key in ("focus", "peak", "falloff")}])
                sources = tuple(HeatSource(**s) for s in definitions)
                temperatures = tuple(tuple(max([ambient] + [
                    source.peak - source.falloff * (abs(x - source.focus[0]) + abs(y - source.focus[1]))
                    for source in sources]) for x in range(width)) for y in range(height))
            scenario = cls(
                name=data["name"], width=width, height=height, base=data["base"],
                victims=data["victims"], walls=data["walls"], temperatures=temperatures,
                max_steps=data.get("max_steps", 100), heat_sources=sources, ambient_temperature=ambient)
            if "scenario_id" in data and data["scenario_id"] != scenario.fingerprint():
                raise ValueError("scenario_id no coincide con el contenido del escenario")
            if "configuration_id" in data and data["configuration_id"] != scenario.configuration_id:
                raise ValueError("configuration_id no coincide con las etiquetas de las personas")
            return scenario
        except (KeyError, TypeError) as error:
            raise ValueError(f"Formato de escenario inválido: {error}") from error

    @property
    def victim_count(self) -> int:
        return len(self.victims)

    def with_victims(self, positions, *, name=None) -> "Scenario":
        """Crea otra configuración validada sin modificar la plantilla."""
        return replace(self, victims=tuple(positions), name=name or self.name)

    def fingerprint(self) -> str:
        """Firma física: independiente del nombre y del orden de etiquetas de personas."""
        return self.scenario_id

    @cached_property
    def scenario_id(self) -> str:
        physical = {"width": self.width, "height": self.height, "base": self.base,
                    "walls": sorted(self.walls), "victims": sorted(self.victims),
                    "temperatures": self.temperatures, "max_steps": self.max_steps}
        return sha256(json.dumps(physical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @cached_property
    def configuration_id(self) -> str:
        """Identidad exacta para reproducción: también distingue el orden de personas."""
        labeled = {"scenario_id": self.fingerprint(), "victims": self.victims}
        return sha256(json.dumps(labeled, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def to_dict(self) -> dict:
        """La exportación conserva exactamente la matriz usada por el motor."""
        return {"schema_version": 2, "scenario_id": self.fingerprint(),
                "configuration_id": self.configuration_id, "name": self.name,
                "width": self.width, "height": self.height, "base": list(self.base),
                "victims": [list(v) for v in self.victims], "walls": [list(w) for w in sorted(self.walls)],
                "temperatures": [list(row) for row in self.temperatures], "max_steps": self.max_steps,
                "heat_sources": [s.to_dict() for s in self.heat_sources],
                "ambient_temperature": self.ambient_temperature}

    def save(self, path: str | Path, *, overwrite=False):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w" if overwrite else "x", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, indent=2, ensure_ascii=False)


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
            outcome = "success" if len(rescued) == self.scenario.victim_count else "running"
            if outcome == "running" and steps >= self.scenario.max_steps:
                outcome = "time_limit"

        self.state = MissionState(tuple(robots), frozenset(rescued), steps, outcome)
        return self.state

    def snapshot(self) -> dict:
        """Datos JSON para futuras interfaces y evaluación; sin referencias mutables."""
        return {
            "schema_version": 2,
            "scenario": self.scenario.name,
            "scenario_id": self.scenario.fingerprint(),
            "configuration_id": self.scenario.configuration_id,
            "victims_total": self.scenario.victim_count,
            "victims": [{"id": i, "position": list(position),
                         "status": "rescued" if i in self.state.rescued else
                         "carried" if any(r.carrying == i for r in self.state.robots) else "pending"}
                        for i, position in enumerate(self.scenario.victims)],
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
