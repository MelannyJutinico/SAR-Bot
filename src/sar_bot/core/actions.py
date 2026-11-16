"""Acciones individuales y codificación de la acción conjunta.

El controlador centralizado elige una sola acción conjunta entre
``5 × 5 = 25`` combinaciones::

    conjunta = 5 × acción_robot_0 + acción_robot_1

Así cada paso global decide el movimiento de ambos robots desde el mismo
estado y el reloj avanza una sola vez.
"""

from __future__ import annotations

from enum import IntEnum

from sar_bot.core.grid import Pos


class Action(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    WAIT = 4


N_ROBOTS = 2
N_ACTIONS = len(Action)
N_JOINT_ACTIONS = N_ACTIONS**N_ROBOTS

DELTAS: dict[Action, Pos] = {
    Action.UP: (-1, 0),
    Action.DOWN: (1, 0),
    Action.LEFT: (0, -1),
    Action.RIGHT: (0, 1),
    Action.WAIT: (0, 0),
}


def target_cell(pos: Pos, action: int) -> Pos:
    """Celda a la que apunta ``action`` desde ``pos``, sin comprobar obstáculos."""
    dr, dc = DELTAS[Action(action)]
    return (pos[0] + dr, pos[1] + dc)


def encode_joint(action_0: int, action_1: int) -> int:
    """Codifica las acciones de los dos robots en un entero de [0, 25)."""
    return N_ACTIONS * int(Action(action_0)) + int(Action(action_1))


def decode_joint(joint: int) -> tuple[Action, Action]:
    """Inversa de :func:`encode_joint`."""
    joint = int(joint)
    if not 0 <= joint < N_JOINT_ACTIONS:
        raise ValueError(f"acción conjunta fuera de rango [0, {N_JOINT_ACTIONS}): {joint}")
    return Action(joint // N_ACTIONS), Action(joint % N_ACTIONS)
