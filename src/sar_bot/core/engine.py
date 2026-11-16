"""Motor de simulación: única fuente de las reglas de movimiento, calor y rescate.

Orden de un paso global (docs/CONTEXTO.md §5):

1. Se reciben las acciones de ambos robots, elegidas desde el mismo estado.
2. Se calculan destinos y se resuelven obstáculos y conflictos de movimiento.
3. Se actualizan posiciones y se aplica la exposición térmica a ambos robots,
   aunque esperen o su movimiento quede bloqueado.
4. Si algún robot queda destruido, el episodio termina en fracaso y no se
   procesan entregas de ese paso.
5. Si ambos siguen operativos, se procesan entregas y recogidas automáticas.
6. Se determina la finalización: éxito, o truncamiento por límite de pasos.
   Un éxito en el último paso permitido cuenta como éxito.

La interfaz, el entorno de Gymnasium y la evaluación consumen este motor;
no deben recalcular daño ni decidir rescates por su cuenta.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sar_bot.core.actions import N_ROBOTS, Action, decode_joint, target_cell
from sar_bot.core.grid import Layout, Pos
from sar_bot.core.rules import RulesConfig
from sar_bot.core.scenario import Scenario


class VictimStatus(str, Enum):
    WAITING = "esperando"
    CARRIED = "transportada"
    RESCUED = "rescatada"


class Outcome(str, Enum):
    RUNNING = "en_curso"
    SUCCESS = "exito"
    DESTROYED = "robot_destruido"
    TIMEOUT = "limite_de_pasos"


@dataclass
class RobotState:
    pos: Pos
    integrity: float
    carrying: int | None = None
    """Índice de la víctima transportada, o ``None``."""
    damage_taken: float = 0.0
    wall_bumps: int = 0
    robot_blocks: int = 0

    @property
    def operational(self) -> bool:
        return self.integrity > 0


@dataclass
class VictimState:
    origin: Pos
    """Celda donde espera la víctima; no cambia mientras la transportan."""
    status: VictimStatus = VictimStatus.WAITING
    carrier: int | None = None


@dataclass(frozen=True)
class MoveResolution:
    positions: tuple[Pos, Pos]
    blocked_by_wall: tuple[bool, bool]
    blocked_by_robot: tuple[bool, bool]


def resolve_moves(layout: Layout, positions: tuple[Pos, Pos], actions: tuple[int, int]) -> MoveResolution:
    """Aplica las convenciones de movimiento simultáneo (docs/CONTEXTO.md §6).

    - Límites y obstáculos impiden el movimiento; el robot se queda.
    - Si ambos apuntan a la misma celda fuera de la base, ambos se quedan.
      Esto cubre entrar en la celda de un robot que no puede salir.
    - Un intercambio directo de posiciones queda bloqueado para ambos.
    - Entrar en la celda que el otro abandona está permitido.
    - En la base ambos robots pueden coincidir.
    """
    desired: list[Pos] = []
    blocked_by_wall: list[bool] = []
    for pos, action in zip(positions, actions):
        target = target_cell(pos, action)
        if target != pos and not layout.is_free(target):
            desired.append(pos)
            blocked_by_wall.append(True)
        else:
            desired.append(target)
            blocked_by_wall.append(False)

    (p0, p1), (d0, d1) = positions, desired
    same_target = d0 == d1 and d0 != layout.base
    swap = p0 != p1 and d0 == p1 and d1 == p0
    if same_target or swap:
        return MoveResolution(
            positions=(p0, p1),
            blocked_by_wall=(blocked_by_wall[0], blocked_by_wall[1]),
            blocked_by_robot=(d0 != p0, d1 != p1),
        )
    return MoveResolution(
        positions=(d0, d1),
        blocked_by_wall=(blocked_by_wall[0], blocked_by_wall[1]),
        blocked_by_robot=(False, False),
    )


@dataclass(frozen=True)
class StepResult:
    """Eventos de un paso global, para recompensa, métricas y visualización."""

    step: int
    actions: tuple[Action, Action]
    positions: tuple[Pos, Pos]
    blocked_by_wall: tuple[bool, bool]
    blocked_by_robot: tuple[bool, bool]
    temperatures: tuple[float, float]
    damage: tuple[float, float]
    picked_up: tuple[int | None, int | None]
    delivered: tuple[int | None, int | None]
    outcome: Outcome
    terminated: bool
    """Fin por éxito o destrucción."""
    truncated: bool
    """Fin por límite de pasos."""

    @property
    def done(self) -> bool:
        return self.terminated or self.truncated


class RescueSim:
    """Estado mutable de un episodio sobre un escenario fijo."""

    def __init__(self, scenario: Scenario, rules: RulesConfig | None = None) -> None:
        self.rules = rules or RulesConfig()
        self.scenario = scenario
        self.reset()

    def reset(self, scenario: Scenario | None = None) -> None:
        """Reinicia el episodio, opcionalmente con otro escenario."""
        if scenario is not None:
            self.scenario = scenario
        self.robots = [
            RobotState(pos=start, integrity=self.rules.initial_integrity) for start in self.scenario.robot_starts
        ]
        self.victims = [VictimState(origin=v) for v in self.scenario.victims]
        self.step_count = 0
        self.outcome = Outcome.RUNNING

    @property
    def layout(self) -> Layout:
        return self.scenario.layout

    @property
    def positions(self) -> tuple[Pos, Pos]:
        return (self.robots[0].pos, self.robots[1].pos)

    @property
    def terminated(self) -> bool:
        return self.outcome in (Outcome.SUCCESS, Outcome.DESTROYED)

    @property
    def truncated(self) -> bool:
        return self.outcome is Outcome.TIMEOUT

    @property
    def done(self) -> bool:
        return self.outcome is not Outcome.RUNNING

    @property
    def rescued_count(self) -> int:
        return sum(v.status is VictimStatus.RESCUED for v in self.victims)

    def step_joint(self, joint_action: int) -> StepResult:
        """Avanza un paso con una acción conjunta de [0, 25)."""
        return self.step(*decode_joint(joint_action))

    def step(self, action_0: int, action_1: int) -> StepResult:
        """Avanza un paso global con una acción por robot."""
        if self.done:
            raise RuntimeError("el episodio terminó; llama a reset() antes de continuar")
        actions = (Action(action_0), Action(action_1))

        # 2. Destinos, obstáculos y conflictos.
        moves = resolve_moves(self.layout, self.positions, actions)

        # 3. Posiciones y exposición térmica de ambos robots.
        self.step_count += 1
        temperatures: list[float] = []
        damage: list[float] = []
        for i, robot in enumerate(self.robots):
            robot.pos = moves.positions[i]
            robot.wall_bumps += int(moves.blocked_by_wall[i])
            robot.robot_blocks += int(moves.blocked_by_robot[i])
            temperature = self.scenario.temperature_at(robot.pos)
            applied = min(self.rules.damage_for(temperature), robot.integrity)
            robot.integrity -= applied
            robot.damage_taken += applied
            temperatures.append(temperature)
            damage.append(applied)

        picked_up: list[int | None] = [None] * N_ROBOTS
        delivered: list[int | None] = [None] * N_ROBOTS

        if not all(robot.operational for robot in self.robots):
            # 4. La destrucción tiene prioridad sobre entregas del mismo paso.
            self.outcome = Outcome.DESTROYED
        else:
            # 5. Entregas y recogidas automáticas.
            for i, robot in enumerate(self.robots):
                if robot.carrying is not None:
                    if robot.pos == self.layout.base:
                        victim = self.victims[robot.carrying]
                        victim.status, victim.carrier = VictimStatus.RESCUED, None
                        delivered[i] = robot.carrying
                        robot.carrying = None
                else:
                    index = self._waiting_victim_at(robot.pos)
                    if index is not None:
                        victim = self.victims[index]
                        victim.status, victim.carrier = VictimStatus.CARRIED, i
                        robot.carrying = index
                        picked_up[i] = index

            # 6. Finalización.
            if all(v.status is VictimStatus.RESCUED for v in self.victims):
                self.outcome = Outcome.SUCCESS
            elif self.step_count >= self.rules.max_steps:
                self.outcome = Outcome.TIMEOUT

        return StepResult(
            step=self.step_count,
            actions=actions,
            positions=self.positions,
            blocked_by_wall=moves.blocked_by_wall,
            blocked_by_robot=moves.blocked_by_robot,
            temperatures=(temperatures[0], temperatures[1]),
            damage=(damage[0], damage[1]),
            picked_up=(picked_up[0], picked_up[1]),
            delivered=(delivered[0], delivered[1]),
            outcome=self.outcome,
            terminated=self.terminated,
            truncated=self.truncated,
        )

    def _waiting_victim_at(self, pos: Pos) -> int | None:
        for index, victim in enumerate(self.victims):
            if victim.status is VictimStatus.WAITING and victim.origin == pos:
                return index
        return None

    def episode_metrics(self) -> dict[str, object]:
        """Resumen del episodio para exportar en la evaluación (docs/CONTEXTO.md §9)."""
        metrics: dict[str, object] = {
            "scenario_id": self.scenario.scenario_id,
            "seed": self.scenario.seed,
            "outcome": self.outcome.value,
            "success": self.outcome is Outcome.SUCCESS,
            "rescued": self.rescued_count,
            "victims": len(self.victims),
            "steps": self.step_count,
        }
        for i, robot in enumerate(self.robots):
            metrics[f"damage_r{i}"] = robot.damage_taken
        metrics["damage_total"] = sum(robot.damage_taken for robot in self.robots)
        for i, robot in enumerate(self.robots):
            metrics[f"integrity_r{i}"] = robot.integrity
        metrics["wall_bumps"] = sum(robot.wall_bumps for robot in self.robots)
        metrics["robot_blocks"] = sum(robot.robot_blocks for robot in self.robots)
        return metrics

    def to_text(self) -> str:
        """Vista de texto para depurar: ``0``/``1`` robots, ``v`` víctima esperando,
        ``B`` base, ``#`` obstáculo, ``*`` dos robots en la misma celda (base)."""
        grid = [list(line) for line in self.layout.to_text().splitlines()]
        for victim in self.victims:
            if victim.status is VictimStatus.WAITING:
                grid[victim.origin[0]][victim.origin[1]] = "v"
        for i, robot in enumerate(self.robots):
            r, c = robot.pos
            grid[r][c] = "*" if grid[r][c] in "01" else str(i)
        header = (
            f"paso {self.step_count}/{self.rules.max_steps} | {self.outcome.value} | "
            + " | ".join(
                f"R{i} integridad={robot.integrity:g} carga={robot.carrying}" for i, robot in enumerate(self.robots)
            )
        )
        return header + "\n" + "\n".join("".join(row) for row in grid)
