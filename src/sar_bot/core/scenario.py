"""Escenario de un episodio: plano, víctimas, calor y posiciones iniciales.

Un escenario es inmutable y se valida al crearse: víctimas en celdas
libres distintas, fuera de la base y alcanzables desde ella; robots en
celdas libres y alcanzables, sin compartir celda salvo en la base.

:func:`generate_scenario` produce escenarios reproducibles a partir de un
plano y una semilla, y descarta los que no parecen viables bajo daño
térmico y límite de pasos (la conectividad por sí sola no basta).
"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from sar_bot.core.actions import N_ROBOTS
from sar_bot.core.grid import Layout, Pos, manhattan
from sar_bot.core.heat import HeatFieldConfig, temperature_field
from sar_bot.core.rules import RulesConfig

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LAYOUTS_DIR = PROJECT_ROOT / "scenarios" / "layouts"


def _as_pos(pos: Pos) -> Pos:
    return (int(pos[0]), int(pos[1]))


@dataclass(frozen=True, eq=False)
class Scenario:
    layout: Layout
    victims: tuple[Pos, ...]
    temperatures: np.ndarray
    """Temperatura en °C de cada celda, fija durante el episodio."""
    hotspot: Pos | None = None
    robot_starts: tuple[Pos, ...] | None = None
    """Posición inicial de cada robot; por defecto ambos en la base."""
    scenario_id: str = "manual"
    seed: int | None = None

    def __post_init__(self) -> None:
        layout = self.layout
        temps = np.array(self.temperatures, dtype=float)
        if temps.shape != layout.shape:
            raise ValueError(f"temperaturas {temps.shape} no coinciden con el plano {layout.shape}")
        temps.setflags(write=False)
        object.__setattr__(self, "temperatures", temps)

        victims = tuple(_as_pos(v) for v in self.victims)
        object.__setattr__(self, "victims", victims)
        starts = self.robot_starts if self.robot_starts is not None else (layout.base,) * N_ROBOTS
        starts = tuple(_as_pos(s) for s in starts)
        object.__setattr__(self, "robot_starts", starts)
        if self.hotspot is not None:
            object.__setattr__(self, "hotspot", _as_pos(self.hotspot))

        reachable = layout.distances_from(layout.base)
        if len(starts) != N_ROBOTS:
            raise ValueError(f"se esperan {N_ROBOTS} posiciones iniciales, hay {len(starts)}")
        for start in starts:
            if start not in reachable:
                raise ValueError(f"inicio de robot {start} no es libre o no es alcanzable desde la base")
        if starts[0] == starts[1] and starts[0] != layout.base:
            raise ValueError("fuera de la base, los robots no pueden compartir celda")
        if not victims:
            raise ValueError("el escenario necesita al menos una víctima")
        if len(set(victims)) != len(victims):
            raise ValueError("las víctimas deben estar en celdas distintas")
        for victim in victims:
            if victim == layout.base:
                raise ValueError("una víctima no puede estar en la base")
            if victim not in reachable:
                raise ValueError(f"víctima {victim} no es libre o no es alcanzable desde la base")
            if victim in starts:
                raise ValueError(f"víctima {victim} coincide con el inicio de un robot")

    def temperature_at(self, pos: Pos) -> float:
        return float(self.temperatures[pos])


def min_damage_path(
    layout: Layout,
    temperatures: np.ndarray,
    rules: RulesConfig,
    start: Pos,
    goal: Pos,
) -> tuple[float, int] | None:
    """Menor ``(daño, pasos)`` para ir de ``start`` a ``goal``, en orden lexicográfico.

    El daño de cada paso es el de la celda de llegada, como en el motor.
    Devuelve ``None`` si ``goal`` no es alcanzable.
    """
    if start == goal:
        return (0.0, 0)
    inf = (float("inf"), float("inf"))
    best: dict[Pos, tuple[float, int]] = {start: (0.0, 0)}
    heap: list[tuple[float, int, Pos]] = [(0.0, 0, start)]
    while heap:
        damage, steps, pos = heapq.heappop(heap)
        if best.get(pos, inf) < (damage, steps):
            continue
        if pos == goal:
            return (damage, steps)
        for nxt in layout.neighbors(pos):
            candidate = (damage + rules.damage_for(float(temperatures[nxt])), steps + 1)
            if candidate < best.get(nxt, inf):
                best[nxt] = candidate
                heapq.heappush(heap, (candidate[0], candidate[1], nxt))
    return None


def estimate_viability(scenario: Scenario, rules: RulesConfig | None = None) -> bool:
    """Estimación optimista de si existe al menos una misión exitosa.

    Prueba cada reparto de víctimas entre los robots y cada orden de visita,
    usando caminos de menor daño por tramo (inicio → víctima → base → ...).
    Cada robot termina en la base y espera allí hasta que acabe el otro.
    Una misión cuenta como viable si cabe en el límite de pasos y ningún
    robot llega a integridad cero.

    Ignora conflictos de movimiento entre robots y la recogida automática
    al pasar sobre otra víctima: es una aproximación. La confirmación
    constructiva es ejecutar una estrategia completa en el motor.
    """
    rules = rules or RulesConfig()
    layout, temps = scenario.layout, scenario.temperatures
    base = layout.base
    cache: dict[tuple[Pos, Pos], tuple[float, int] | None] = {}

    def leg(a: Pos, b: Pos) -> tuple[float, int] | None:
        if (a, b) not in cache:
            cache[(a, b)] = min_damage_path(layout, temps, rules, a, b)
        return cache[(a, b)]

    def robot_plan(start: Pos, order: tuple[Pos, ...]) -> tuple[float, int] | None:
        stops = [start]
        for victim in order:
            stops.extend([victim, base])
        if not order:
            stops.append(base)
        damage, steps = 0.0, 0
        for a, b in zip(stops, stops[1:]):
            cost = leg(a, b)
            if cost is None:
                return None
            damage, steps = damage + cost[0], steps + cost[1]
        return (damage, steps)

    base_wait_damage = rules.damage_for(scenario.temperature_at(base))
    victims = scenario.victims
    for assignment in itertools.product(range(N_ROBOTS), repeat=len(victims)):
        options: list[list[tuple[float, int]]] = []
        for robot in range(N_ROBOTS):
            mine = [v for v, owner in zip(victims, assignment) if owner == robot]
            plans = [robot_plan(scenario.robot_starts[robot], order) for order in itertools.permutations(mine)]
            plans = [p for p in plans if p is not None]
            if not plans:
                break
            options.append(plans)
        else:
            for combo in itertools.product(*options):
                mission_steps = max(steps for _, steps in combo)
                if mission_steps > rules.max_steps:
                    continue
                if all(
                    damage + base_wait_damage * (mission_steps - steps) < rules.initial_integrity
                    for damage, steps in combo
                ):
                    return True
    return False


def generate_scenario(
    layout: Layout,
    seed: int,
    *,
    heat: HeatFieldConfig | None = None,
    rules: RulesConfig | None = None,
    n_victims: int = 2,
    min_victim_base_distance: int = 2,
    require_viable: bool = True,
    max_attempts: int = 500,
) -> Scenario:
    """Escenario reproducible: misma semilla y plano ⇒ mismo escenario.

    Sortea víctimas (a distancia de camino ≥ ``min_victim_base_distance`` de
    la base) y un foco térmico (a distancia Manhattan ≥
    ``heat.min_base_distance``). Ambos robots empiezan en la base.
    """
    heat = heat or HeatFieldConfig()
    rules = rules or RulesConfig()
    rng = np.random.default_rng(int(seed))
    reachable = layout.distances_from(layout.base)
    victim_cells = sorted(p for p, d in reachable.items() if d >= min_victim_base_distance)
    hotspot_cells = sorted(p for p in reachable if manhattan(p, layout.base) >= heat.min_base_distance)
    if len(victim_cells) < n_victims:
        raise ValueError(f"plano '{layout.name}': no hay {n_victims} celdas válidas para víctimas")
    if not hotspot_cells:
        raise ValueError(f"plano '{layout.name}': no hay celdas válidas para el foco térmico")

    for _ in range(max_attempts):
        chosen = rng.choice(len(victim_cells), size=n_victims, replace=False)
        victims = tuple(victim_cells[int(i)] for i in chosen)
        hotspot = hotspot_cells[int(rng.integers(len(hotspot_cells)))]
        scenario = Scenario(
            layout=layout,
            victims=victims,
            temperatures=temperature_field(layout, hotspot, heat),
            hotspot=hotspot,
            scenario_id=f"{layout.name}/s{int(seed)}",
            seed=int(seed),
        )
        if not require_viable or estimate_viability(scenario, rules):
            return scenario
    raise RuntimeError(f"plano '{layout.name}', semilla {seed}: sin escenario viable tras {max_attempts} intentos")


def load_layouts(directory: str | Path | None = None) -> dict[str, Layout]:
    """Carga los planos ``*.txt`` de ``scenarios/layouts`` (o del directorio dado)."""
    directory = Path(directory) if directory is not None else LAYOUTS_DIR
    files = sorted(directory.glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"no hay planos .txt en {directory}")
    return {path.stem: Layout.from_file(path) for path in files}
