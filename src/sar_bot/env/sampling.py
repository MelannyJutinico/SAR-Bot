"""Particiones de escenarios: entrenamiento, validación y prueba.

- Validación y prueba son listas fijas: cada plano × cada semilla de su rango.
- Entrenamiento sortea plano y semilla con el generador del entorno y
  descarta cualquier escenario cuya misión coincida con uno de validación
  o prueba (mismo plano, mismas celdas de víctimas y mismo foco).
"""

from __future__ import annotations

from typing import Literal

import numpy as np

from sar_bot.config import ProjectConfig
from sar_bot.core.grid import Layout
from sar_bot.core.scenario import Scenario, generate_scenario, load_layouts

Split = Literal["train", "validation", "test"]
SPLITS: tuple[str, ...] = ("train", "validation", "test")


def scenario_key(scenario: Scenario) -> tuple:
    """Identidad de la misión, independiente del orden de las víctimas."""
    return (scenario.layout.name, frozenset(scenario.victims), scenario.hotspot)


class ScenarioSampler:
    def __init__(self, config: ProjectConfig, split: Split, layouts: dict[str, Layout] | None = None) -> None:
        if split not in SPLITS:
            raise ValueError(f"partición desconocida: {split!r}; opciones: {SPLITS}")
        all_layouts = layouts if layouts is not None else load_layouts()
        missing = [name for name in config.scenarios.layouts if name not in all_layouts]
        if missing:
            raise ValueError(f"planos no encontrados: {missing}")
        self.config = config
        self.split = split
        self.layouts = [all_layouts[name] for name in config.scenarios.layouts]
        shapes = {layout.shape for layout in self.layouts}
        if len(shapes) != 1:
            raise ValueError(f"todos los planos deben tener el mismo tamaño; hay {sorted(shapes)}")
        self.shape = shapes.pop()

        self.fixed: list[Scenario] = []
        self._held_out: set[tuple] = set()
        if split == "train":
            for seeds in (config.scenarios.validation_seeds, config.scenarios.test_seeds):
                self._held_out |= {scenario_key(s) for s in self._fixed_list(seeds)}
        else:
            seeds = config.scenarios.validation_seeds if split == "validation" else config.scenarios.test_seeds
            self.fixed = self._fixed_list(seeds)
        self._cursor = 0

    def _generate(self, layout: Layout, seed: int) -> Scenario:
        return generate_scenario(
            layout,
            seed,
            heat=self.config.heat,
            rules=self.config.rules,
            n_victims=self.config.scenarios.n_victims,
            min_victim_base_distance=self.config.scenarios.min_victim_base_distance,
        )

    def _fixed_list(self, seeds: tuple[int, int]) -> list[Scenario]:
        return [self._generate(layout, seed) for seed in range(*seeds) for layout in self.layouts]

    def is_held_out(self, scenario: Scenario) -> bool:
        return scenario_key(scenario) in self._held_out

    def sample(self, rng: np.random.Generator) -> Scenario:
        """Entrenamiento: escenario aleatorio fuera de validación y prueba.
        Validación y prueba: siguiente escenario de la lista fija, en ciclo."""
        if self.split != "train":
            scenario = self.fixed[self._cursor % len(self.fixed)]
            self._cursor += 1
            return scenario
        while True:
            layout = self.layouts[int(rng.integers(len(self.layouts)))]
            scenario = self._generate(layout, int(rng.integers(0, 2**31 - 1)))
            if not self.is_held_out(scenario):
                return scenario
