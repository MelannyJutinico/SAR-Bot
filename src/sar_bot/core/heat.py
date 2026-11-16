"""Campo térmico de un foco fijo, precomputado por episodio.

Modelo inicial (abstracto, ajustable por la persona 2)::

    T(celda) = max(ambiente, pico - gradiente × distancia_manhattan(celda, foco))

Con los valores por defecto (25 °C, 95 °C, 20 °C por casilla):

    distancia 0 → 95 °C (tasa 10)
    distancia 1 → 75 °C (tasa 5)
    distancia 2 → 55 °C (tasa 2)
    distancia ≥3 → ≤35 °C (tasa 0)

La base se configura como celda segura: su temperatura es la ambiente.
El calor no depende del tiempo ni de la velocidad de reproducción.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sar_bot.core.grid import Layout, Pos


@dataclass(frozen=True)
class HeatFieldConfig:
    ambient: float = 25.0
    peak: float = 95.0
    gradient: float = 20.0
    """Descenso de temperatura en °C por casilla de distancia Manhattan al foco."""
    min_base_distance: int = 3
    """Distancia Manhattan mínima entre el foco y la base al generar escenarios."""
    safe_base: bool = True

    def __post_init__(self) -> None:
        if self.peak < self.ambient:
            raise ValueError("la temperatura pico no puede ser menor que la ambiente")
        if self.gradient < 0:
            raise ValueError("el gradiente no puede ser negativo")


def temperature_field(layout: Layout, hotspot: Pos, config: HeatFieldConfig | None = None) -> np.ndarray:
    """Matriz (alto, ancho) de temperaturas en °C para un foco dado."""
    config = config or HeatFieldConfig()
    rows, cols = np.indices(layout.shape)
    distance = np.abs(rows - hotspot[0]) + np.abs(cols - hotspot[1])
    temps = np.maximum(config.ambient, config.peak - config.gradient * distance).astype(float)
    if config.safe_base:
        temps[layout.base] = config.ambient
    return temps
