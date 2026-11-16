"""Plano estático del edificio: celdas libres, obstáculos y base.

Las posiciones son tuplas ``(fila, columna)``; la fila 0 está arriba.
Un plano no contiene víctimas ni calor: esos elementos varían por
episodio y se definen en :mod:`sar_bot.core.scenario`.

Formato de texto de un plano (un carácter por celda)::

    .  celda libre
    #  obstáculo
    B  base (salida compartida); exactamente una
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np

Pos = tuple[int, int]

FREE_CHAR = "."
WALL_CHAR = "#"
BASE_CHAR = "B"

_NEIGHBOR_DELTAS: tuple[Pos, ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))


def manhattan(a: Pos, b: Pos) -> int:
    """Distancia Manhattan entre dos posiciones."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


@dataclass(frozen=True, eq=False)
class Layout:
    """Plano inmutable: matriz de obstáculos y posición de la base."""

    name: str
    walls: np.ndarray
    """Matriz booleana (alto, ancho); ``True`` indica obstáculo."""
    base: Pos

    def __post_init__(self) -> None:
        walls = np.array(self.walls, dtype=bool)
        if walls.ndim != 2 or walls.size == 0:
            raise ValueError("el plano debe ser una matriz 2D no vacía")
        walls.setflags(write=False)
        object.__setattr__(self, "walls", walls)
        object.__setattr__(self, "base", (int(self.base[0]), int(self.base[1])))
        if not self.is_free(self.base):
            raise ValueError(f"la base {self.base} debe ser una celda libre dentro del plano")

    @property
    def shape(self) -> tuple[int, int]:
        return (int(self.walls.shape[0]), int(self.walls.shape[1]))

    @property
    def height(self) -> int:
        return self.shape[0]

    @property
    def width(self) -> int:
        return self.shape[1]

    def in_bounds(self, pos: Pos) -> bool:
        row, col = pos
        return 0 <= row < self.height and 0 <= col < self.width

    def is_free(self, pos: Pos) -> bool:
        """``True`` si la posición está dentro del plano y no es obstáculo."""
        return self.in_bounds(pos) and not bool(self.walls[pos])

    def free_cells(self) -> list[Pos]:
        """Celdas libres en orden fila-columna (incluye la base)."""
        rows, cols = np.nonzero(~self.walls)
        return [(int(r), int(c)) for r, c in zip(rows, cols)]

    def neighbors(self, pos: Pos) -> list[Pos]:
        """Vecinos libres en 4 direcciones."""
        result = []
        for dr, dc in _NEIGHBOR_DELTAS:
            nxt = (pos[0] + dr, pos[1] + dc)
            if self.is_free(nxt):
                result.append(nxt)
        return result

    def distances_from(self, start: Pos) -> dict[Pos, int]:
        """Distancias de camino (BFS) desde ``start`` a cada celda alcanzable."""
        if not self.is_free(start):
            raise ValueError(f"{start} no es una celda libre")
        dist = {start: 0}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for nxt in self.neighbors(current):
                if nxt not in dist:
                    dist[nxt] = dist[current] + 1
                    queue.append(nxt)
        return dist

    def is_connected(self) -> bool:
        """``True`` si todas las celdas libres son alcanzables desde la base."""
        return len(self.distances_from(self.base)) == len(self.free_cells())

    def to_text(self) -> str:
        lines = []
        for r in range(self.height):
            chars = []
            for c in range(self.width):
                if (r, c) == self.base:
                    chars.append(BASE_CHAR)
                elif self.walls[r, c]:
                    chars.append(WALL_CHAR)
                else:
                    chars.append(FREE_CHAR)
            lines.append("".join(chars))
        return "\n".join(lines)

    @classmethod
    def from_text(cls, name: str, text: str) -> Layout:
        rows = [line.strip() for line in text.strip().splitlines() if line.strip()]
        if not rows:
            raise ValueError(f"plano '{name}' vacío")
        width = len(rows[0])
        if any(len(row) != width for row in rows):
            raise ValueError(f"plano '{name}': todas las filas deben tener el mismo ancho")
        walls = np.zeros((len(rows), width), dtype=bool)
        bases = []
        for r, row in enumerate(rows):
            for c, char in enumerate(row):
                if char == WALL_CHAR:
                    walls[r, c] = True
                elif char == BASE_CHAR:
                    bases.append((r, c))
                elif char != FREE_CHAR:
                    raise ValueError(f"plano '{name}': carácter desconocido {char!r} en {(r, c)}")
        if len(bases) != 1:
            raise ValueError(f"plano '{name}': debe haber exactamente una base, hay {len(bases)}")
        return cls(name=name, walls=walls, base=bases[0])

    @classmethod
    def from_file(cls, path: str | Path) -> Layout:
        path = Path(path)
        return cls.from_text(path.stem, path.read_text(encoding="utf-8"))
